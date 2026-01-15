#!/usr/bin/env python3
"""
SCuBA Scoring on top of CISA ScubaGoggles JSON results.

Usage:
  python scubascore.py \
    --input ScubaResults-1234.json \
    --weights weights.yaml \
    --service-weights service_weights.yaml \
    --compensating compensating.yaml \
    --out-prefix output/scuba

Outputs:
  - <prefix>_scores.json  (overall + per-service + failed-topics)
  - <prefix>_scores.csv   (per-service table)
  - <prefix>_summary.html (quick executive view)

Notes:
- The script is schema-tolerant. It looks for rule entries with fields like:
    rule_id / id, verdict / result, service, severity / priority (optional)
- If "service" is missing, it tries to infer from rule_id (e.g., "gws.gmail.*" -> "gmail").
- Verdicts supported (case-insensitive): PASS, FAIL, N/A (/ NOT APPLICABLE), UNKNOWN/ERROR.
- Unknown entries are skipped but surfaced in "data_quality".
"""
import argparse, json, pathlib, sys, csv, datetime, re
from collections import defaultdict

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_yaml(path, default=None):
    if not path:
        return default or {}
    import yaml  # stdlib in this environment may not include pyyaml in some contexts; fallback to simple parser if needed.
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def normalize_verdict(v):
    if v is None:
        return "UNKNOWN"
    v = str(v).strip().upper()
    # Handle common variants
    if v in {"PASS", "PASSED", "TRUE"}:
        return "PASS"
    if v in {"FAIL", "FAILED", "FALSE"}:
        return "FAIL"
    if v in {"N/A", "NA", "NOT APPLICABLE"}:
        return "NA"
    if v in {"UNKNOWN", "ERROR"}:
        return "UNKNOWN"
    return v

def infer_service(rule_id):
    if not rule_id:
        return None
    # Common SCuBA prefixes like gws.gmail.*, gws.drive.*, gws.common.*
    m = re.match(r"^[a-zA-Z0-9]+\.([a-z_]+)\.?", rule_id)
    if m:
        candidate = m.group(1)
        # Map common names to canonical service keys
        mapping = {
            "gmail": "gmail", "drive": "drive", "chat": "chat", "meet": "meet",
            "calendar": "calendar", "groups": "groups", "classroom": "classroom",
            "sites": "sites", "common": "common"
        }
        return mapping.get(candidate, candidate)
    return None

def iter_rules(scuba_json):
    """
    Try to yield a normalized stream of rule dicts:
    { 'rule_id': str, 'service': str|None, 'verdict': 'PASS'|'FAIL'|'NA'|'UNKNOWN', 'severity': str|None }
    """
    # Heuristics: results may be in top-level list or nested under keys like 'results', 'rules', 'checks'
    candidates = []
    if isinstance(scuba_json, list):
        candidates = scuba_json
    elif isinstance(scuba_json, dict):
        for k in ["results", "rules", "checks", "findings", "items"]:
            if isinstance(scuba_json.get(k), list):
                candidates = scuba_json[k]
                break
        if not candidates:
            # Some formats: {"services": {"gmail": {"rules":[...]}, ...}}
            services_obj = scuba_json.get("services")
            if isinstance(services_obj, dict):
                for svc, obj in services_obj.items():
                    rules = obj.get("rules") or obj.get("results") or obj.get("checks")
                    if isinstance(rules, list):
                        for r in rules:
                            yield normalize_rule(r, default_service=svc)
                return
    # Fallback if still empty: maybe it's a dict with arbitrary arrays; flatten any lists
    if not candidates:
        for v in scuba_json.values() if isinstance(scuba_json, dict) else []:
            if isinstance(v, list):
                candidates = v
                break

    for r in candidates or []:
        yield normalize_rule(r)

def normalize_rule(r, default_service=None):
    # Extract identifiers
    rule_id = r.get("rule_id") or r.get("id") or r.get("rule") or r.get("name")
    verdict = normalize_verdict(r.get("verdict") or r.get("result") or r.get("status"))
    service = (r.get("service") or r.get("product") or r.get("category") or default_service)
    severity = r.get("severity") or r.get("priority") or r.get("weight_class")

    if not service:
        service = infer_service(rule_id)

    return {
        "rule_id": rule_id,
        "verdict": verdict,
        "service": service,
        "severity": severity
    }

def compute_scores(scuba_json, weights_map, service_weights, compensating):
    """
    Compute weighted SCuBA security compliance scores from ScubaGoggles JSON results.

    This is the core scoring algorithm that transforms raw compliance data into quantified
    risk scores. It applies a risk-based weighting model to rule pass/fail verdicts, accounts
    for compensating controls, and produces both per-service and overall security scores.

    Algorithm Overview:
    -------------------
    1. **Rule Processing**: Iterate through all compliance rules in the input JSON.
       - Extract rule_id, verdict (PASS/FAIL/NA/UNKNOWN), service, and severity.
       - Normalize verdicts to handle common variations (e.g., "PASSED" -> "PASS").
       - Infer service from rule_id if not explicitly provided (e.g., "gws.gmail.*" -> "gmail").

    2. **Weight Assignment**: Assign a numeric weight to each rule based on its severity/risk.
       - Look up exact rule_id match in weights_map (e.g., "gws.gmail.dmarc_enforced" -> 5).
       - If no exact match, use longest prefix match (e.g., "gws.common." -> 3).
       - Default to 1.0 if no match found.

    3. **Verdict Scoring**: Calculate contribution to service scores based on verdict.
       - PASS: Add full weight to both passed_weight and evaluated_weight.
       - FAIL: Add 0% to passed_weight, full weight to evaluated_weight.
       - FAIL with compensating control: Add 50% of weight to passed_weight (partial credit).
       - N/A: Skip rule entirely (not counted in score).
       - UNKNOWN/ERROR: Track in data_quality metrics but skip scoring.

    4. **Service Score Calculation**: For each service, compute percentage score.
       - Formula: (passed_weight / evaluated_weight) * 100
       - Example: If gmail has 80 passed_weight and 100 evaluated_weight -> 80% score.

    5. **Overall Score Aggregation**: Combine service scores using service weights.
       - Formula: Σ(service_score × service_weight) / Σ(service_weights)
       - Example: gmail (80%, weight=0.20) + drive (90%, weight=0.20) + ...
       - Only includes services that have evaluated rules.

    Compensating Controls:
    ----------------------
    Rules listed in the compensating map receive partial credit even when they fail.
    This acknowledges external mitigations (e.g., third-party DLP, network controls).
    - Compensating FAIL contributes 50% of its weight to the passed_weight.
    - Non-compensating FAIL contributes 0%.

    Parameters:
    -----------
    scuba_json : dict or list
        Raw ScubaGoggles JSON results. Can be a list of rules or nested structure.
        The function is schema-tolerant and will search for rules under various keys
        (e.g., "results", "rules", "checks", or nested under "services").

    weights_map : dict or None
        Mapping of rule IDs (or prefixes) to numeric weights.
        Format: {"weights": {"gws.gmail.rule1": 5, "gws.common.": 3, ...}}
        or bare dict: {"gws.gmail.rule1": 5, ...}
        Supports prefix matching: "gws.common." matches all "gws.common.*" rules.

    service_weights : dict or None
        Mapping of service names to their relative importance (0.0-1.0).
        Format: {"service_weights": {"gmail": 0.20, "drive": 0.20, ...}}
        or bare dict: {"gmail": 0.20, ...}
        Values typically sum to 1.0 but will be normalized automatically.

    compensating : dict or None
        Mapping of rule IDs that have compensating controls.
        Format: {"compensating": {"rule_id1": true, "rule_id2": true, ...}}
        or bare dict: {"rule_id1": true, ...}
        Rules in this list get 50% credit when they fail.

    Returns:
    --------
    dict
        Comprehensive scoring results with the following structure:
        {
            "generated_at": str,              # ISO8601 timestamp
            "overall_score": float or None,   # 0-100 percentage, weighted mean of services
            "per_service": {
                "service_name": {
                    "score": float or None,           # 0-100 percentage for this service
                    "evaluated_weight": float,        # Total weight of evaluated rules
                    "passed_weight": float,           # Weight that passed (including partial)
                    "passed_count": int,              # Number of rules that passed
                    "failed_count": int               # Number of rules that failed
                },
                ...
            },
            "data_quality": {
                "unknown_or_error_entries": int,  # Count of unparseable/unknown verdicts
                "total_entries_seen": int         # Total rules processed
            }
        }

    Examples:
    ---------
    >>> data = load_json("ScubaResults.json")
    >>> weights = {"weights": {"gws.gmail.dmarc": 5, "gws.common.": 3}}
    >>> svc_weights = {"service_weights": {"gmail": 0.3, "drive": 0.3, "common": 0.4}}
    >>> compensating = {"compensating": {"gws.gmail.legacy_auth": True}}
    >>> results = compute_scores(data, weights, svc_weights, compensating)
    >>> print(results["overall_score"])
    85.5

    Notes:
    ------
    - All scores are rounded to 2 decimal places.
    - Services with no evaluated rules will have score=None.
    - Overall score is None if no services have valid scores.
    - The function is designed to be robust against schema variations and missing fields.
    """
    # Prepare weight lookups
    default_weight = 1.0
    comp = compensating or {}
    comp_map = comp.get("compensating", comp)  # allow bare mapping

    per_service = defaultdict(lambda: {"W_pass": 0.0, "W_eval": 0.0, "passed": [], "failed": []})
    unknown_or_na = 0
    total_rules = 0

    # Normalize weights_map
    weight_map = (weights_map or {}).get("weights", weights_map) or {}

    for entry in iter_rules(scuba_json):
        total_rules += 1
        rule_id = entry["rule_id"]
        verdict = entry["verdict"]
        service = entry["service"] or "unspecified"

        # Weight Precedence: specific rule_id > prefix match (longest wins) > default (1.0)
        # Step 1: Try exact rule_id match (highest precedence)
        W = weight_map.get(rule_id)
        if W is None and rule_id:
            # Step 2: Try prefix-based mapping (e.g., 'gws.common.' matches 'gws.common.rule1')
            # If multiple prefixes match, use the longest one (most specific)
            best_prefix = ""
            for k in weight_map.keys():
                if rule_id.startswith(k) and len(k) > len(best_prefix):
                    best_prefix = k
            W = weight_map.get(best_prefix, default_weight)
        if W is None:
            # Step 3: Fallback to default weight (lowest precedence)
            W = default_weight

        if verdict == "PASS":
            per_service[service]["W_pass"] += W
            per_service[service]["W_eval"] += W
            per_service[service]["passed"].append((rule_id, W))
        elif verdict == "FAIL":
            # Compensating control => grant 50% credit
            adjusted = 0.5 if rule_id in comp_map else 0.0
            per_service[service]["W_pass"] += W * adjusted
            per_service[service]["W_eval"] += W
            per_service[service]["failed"].append((rule_id, W, adjusted > 0))
        elif verdict in {"NA"}:
            # not counted
            pass
        else:
            unknown_or_na += 1

    # Compute service scores
    per_service_scores = {}
    for svc, agg in per_service.items():
        if agg["W_eval"] > 0:
            score = (agg["W_pass"] / agg["W_eval"]) * 100.0
        else:
            score = None  # no evaluated items
        per_service_scores[svc] = {
            "score": round(score, 2) if score is not None else None,
            "evaluated_weight": round(agg["W_eval"], 2),
            "passed_weight": round(agg["W_pass"], 2),
            "passed_count": len(agg["passed"]),
            "failed_count": len(agg["failed"]),
        }

    # Overall score as weighted mean of available services
    sw = (service_weights or {}).get("service_weights", service_weights) or {}
    total_weight = 0.0
    weighted_sum = 0.0
    for svc, w in sw.items():
        if svc in per_service_scores and per_service_scores[svc]["score"] is not None:
            total_weight += float(w)
            weighted_sum += float(w) * per_service_scores[svc]["score"]
    overall = (weighted_sum / total_weight) if total_weight > 0 else None

    results = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "overall_score": round(overall, 2) if overall is not None else None,
        "per_service": per_service_scores,
        "data_quality": {
            "unknown_or_error_entries": unknown_or_na,
            "total_entries_seen": total_rules
        }
    }
    return results

def write_csv(prefix, per_service_scores):
    path = f"{prefix}_scores.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Service", "Score", "EvaluatedWeight", "PassedWeight", "PassedCount", "FailedCount"])
        for svc, d in sorted(per_service_scores.items()):
            writer.writerow([svc, d["score"], d["evaluated_weight"], d["passed_weight"], d["passed_count"], d["failed_count"]])
    return path

def write_html(prefix, results):
    path = f"{prefix}_summary.html"
    overall = results["overall_score"]
    rows = []
    for svc, d in sorted(results["per_service"].items()):
        score = d["score"]
        rows.append(f"<tr><td>{svc}</td><td>{'' if score is None else round(score,2)}</td><td>{d['evaluated_weight']}</td><td>{d['passed_weight']}</td><td>{d['passed_count']}</td><td>{d['failed_count']}</td></tr>")
    dq = results["data_quality"]
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>SCuBA Score Summary</title>
  <style>
    body{{font-family:system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin:40px;}}
    .card{{border:1px solid #ddd; border-radius:12px; padding:16px; margin-bottom:24px; box-shadow:0 2px 8px rgba(0,0,0,.05);}}
    table{{border-collapse:collapse; width:100%;}}
    th,td{{border:1px solid #e5e7eb; padding:8px; text-align:left;}}
    th{{background:#f9fafb;}}
    .overall{{font-size:32px; font-weight:700;}}
    .muted{{color:#6b7280;}}
  </style>
</head>
<body>
  <div class="card">
    <div class="overall">Overall SCuBA Score: {'' if overall is None else round(overall,2)}</div>
    <div class="muted">Generated at: {results["generated_at"]}</div>
  </div>
  <div class="card">
    <h2>Per-Service Scores</h2>
    <table>
      <thead><tr><th>Service</th><th>Score</th><th>Evaluated Weight</th><th>Passed Weight</th><th>Passed</th><th>Failed</th></tr></thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>
  <div class="card">
    <h3>Data Quality</h3>
    <p>Unknown/Error entries: {dq["unknown_or_error_entries"]} / Total entries seen: {dq["total_entries_seen"]}</p>
  </div>
</body>
</html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Path to ScubaGoggles JSON results")
    p.add_argument("--weights", required=False, help="weights.yaml mapping rule_id/prefix to numeric weight")
    p.add_argument("--service-weights", required=False, help="service_weights.yaml with service_weights mapping")
    p.add_argument("--compensating", required=False, help="compensating.yaml (optional)")
    p.add_argument("--out-prefix", required=True, help="Output file prefix (directories must exist)")
    args = p.parse_args()

    data = load_json(args.input)
    weights = load_yaml(args.weights, default={})
    service_weights = load_yaml(args.service_weights, default={
        "service_weights": {
            "gmail": 0.20, "drive": 0.20, "common": 0.20, "groups": 0.10,
            "chat": 0.10, "meet": 0.05, "calendar": 0.05, "classroom": 0.05, "sites": 0.05
        }
    })
    compensating = load_yaml(args.compensating, default={})

    results = compute_scores(data, weights, service_weights, compensating)

    # Write outputs
    prefix = args.out_prefix
    pathlib.Path(prefix).parent.mkdir(parents=True, exist_ok=True)
    json_path = f"{prefix}_scores.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    csv_path = write_csv(prefix, results["per_service"])
    html_path = write_html(prefix, results)

    print(json.dumps({
        "json": json_path,
        "csv": csv_path,
        "html": html_path,
        "overall_score": results["overall_score"]
    }, indent=2))

if __name__ == "__main__":
    main()
