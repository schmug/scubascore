SCuBA Scoring Kit
==================

Files:
- scubascore.py
- weights.yaml
- service_weights.yaml
- compensating.yaml

Quick start:
1) Run ScubaGoggles to generate a JSON like 'ScubaResults-XXXX.json'.
2) Edit weights.yaml to reflect your risk model (Critical=5, High=3, Medium=2, Low=1).
3) (Optional) Add compensating controls in compensating.yaml.
4) Execute:

   python scubascore.py --input ScubaResults-XXXX.json \
     --weights weights.yaml \
     --service-weights service_weights.yaml \
     --compensating compensating.yaml \
     --out-prefix results/tenant_scuba

Outputs:
- results/tenant_scuba_scores.json
- results/tenant_scuba_scores.csv
- results/tenant_scuba_summary.html

Notes:
- The parser is schema-tolerant and attempts to infer 'service' from rule_id if missing.
- Verdicts supported: PASS, FAIL, NA (not applicable), UNKNOWN/ERROR (excluded from denominator).
- You can map entire prefixes (e.g., 'gws.common.') in weights.yaml to avoid listing every rule.
