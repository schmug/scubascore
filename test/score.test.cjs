"use strict";

// Regression tests for the ScubaScore scoring engine.
//
// The engine is the pure, DOM-free region of index.html delimited by the
// "// === SCORING ENGINE START/END ===" markers, which ends with a
// `module.exports = { ... }`. To prove the SHIPPED file is correct (not a
// copy), this test extracts that exact byte range at runtime, writes it to a
// temp .cjs, and `require`s it. It never forks the scoring logic into a second
// source file, so index.html stays the single source of truth.
//
// Run with:  node --test   (or)  npm test

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const REPO_ROOT = path.join(__dirname, "..");
const INDEX_HTML = path.join(REPO_ROOT, "index.html");
const START_MARKER = "// === SCORING ENGINE START ===";
const END_MARKER = "// === SCORING ENGINE END ===";

// --- Extract the engine region from the shipped index.html ---
function loadEngine() {
  const html = fs.readFileSync(INDEX_HTML, "utf8");
  const start = html.indexOf(START_MARKER);
  const end = html.indexOf(END_MARKER);
  assert.ok(start !== -1, "SCORING ENGINE START marker not found in index.html");
  assert.ok(end !== -1, "SCORING ENGINE END marker not found in index.html");
  assert.ok(end > start, "END marker must come after START marker");
  // Slice [start, end): the module.exports line lives between the markers, so
  // it is included. This must match the byte-slice that was verified by hand.
  const region = html.slice(start, end);
  const tmp = path.join(
    fs.mkdtempSync(path.join(os.tmpdir(), "scubascore-")),
    "engine.cjs"
  );
  fs.writeFileSync(tmp, region);
  try {
    return require(tmp);
  } finally {
    // Best-effort cleanup; the module is already cached in memory.
    try { fs.rmSync(path.dirname(tmp), { recursive: true, force: true }); } catch (e) { /* ignore */ }
  }
}

const eng = loadEngine();

// A bad extraction (e.g. markers moved, export dropped) should fail here with a
// clear message instead of a downstream "undefined is not a function".
test("engine extraction exposes the expected functions", () => {
  for (const fn of ["normalizeVerdict", "inferService", "normalizeRule", "iterRules", "resolveWeight", "computeScores", "topFailures"]) {
    assert.strictEqual(typeof eng[fn], "function", `expected eng.${fn} to be a function`);
  }
});

test("normalizeVerdict canonicalizes verdict spellings", () => {
  assert.strictEqual(eng.normalizeVerdict("Pass"), "PASS");
  assert.strictEqual(eng.normalizeVerdict("passed"), "PASS");
  assert.strictEqual(eng.normalizeVerdict("TRUE"), "PASS");
  assert.strictEqual(eng.normalizeVerdict("Fail"), "FAIL");
  assert.strictEqual(eng.normalizeVerdict("false"), "FAIL");
  assert.strictEqual(eng.normalizeVerdict("N/A"), "NA");
  assert.strictEqual(eng.normalizeVerdict("Not Applicable"), "NA");
  assert.strictEqual(eng.normalizeVerdict(null), "UNKNOWN");
  // Unrecognized verdicts (e.g. ScubaGoggles "Warning") pass through uppercased
  // and are counted as unknown/unscored, not pass or fail.
  assert.strictEqual(eng.normalizeVerdict("Warning"), "WARNING");
});

test("inferService matches the service segment case-insensitively", () => {
  // Real ScubaGoggles/ScubaGear IDs use UPPERCASE service segments; these must
  // map to the lowercase service-weight preset keys.
  assert.strictEqual(eng.inferService("GWS.GMAIL.1.1v0.6"), "gmail");
  assert.strictEqual(eng.inferService("MS.AAD.1.1v1"), "aad");
  assert.strictEqual(eng.inferService(null), null);
});

test("resolveWeight: exact > longest-prefix > default", () => {
  const ruleWeights = {
    "MS.AAD.": 1.5,        // prefix
    "MS.AAD.1.1v1": 3,     // exact, longer than the prefix
    "GWS.GMAIL.": 1.2,
  };
  // Exact match wins even though a prefix also matches.
  assert.strictEqual(eng.resolveWeight("MS.AAD.1.1v1", ruleWeights, 1), 3);
  // No exact match -> longest matching prefix.
  assert.strictEqual(eng.resolveWeight("MS.AAD.9.9v1", ruleWeights, 1), 1.5);
  // No match at all -> the supplied default.
  assert.strictEqual(eng.resolveWeight("ZZZ.NONE.1.1v1", ruleWeights, 1), 1);
});

test("compensating controls earn 50% credit on failure", () => {
  const data = { results: [{ rule_id: "X.SVC.1.1", verdict: "Fail" }] };
  const weights = { "X.SVC.1.1": 2 };
  const svc = { svc: 1 };
  // Compensated: failed weight contributes 50% to the numerator, full to denom.
  const compensated = eng.computeScores(data, weights, svc, new Set(["X.SVC.1.1"]), 1);
  assert.strictEqual(compensated.overall_score, 50);
  // Uncompensated: a plain failure contributes 0%.
  const plain = eng.computeScores(data, weights, svc, new Set(), 1);
  assert.strictEqual(plain.overall_score, 0);
});

test("per-service percentage and service-weighted overall", () => {
  // Service aaa scores 100, bbb scores 0. With weights 3 and 1 the overall is
  // (3*100 + 1*0) / (3+1) = 75.
  const data = {
    results: [
      { rule_id: "A.AAA.1.1", verdict: "Pass" },
      { rule_id: "B.BBB.1.1", verdict: "Fail" },
    ],
  };
  const result = eng.computeScores(data, {}, { aaa: 3, bbb: 1 }, new Set(), 1);
  assert.strictEqual(result.per_service.aaa.score, 100);
  assert.strictEqual(result.per_service.bbb.score, 0);
  assert.strictEqual(result.overall_score, 75);
});

test("services absent from the service-weight set are excluded from the overall", () => {
  // bbb has a score but no service weight, so it must not affect the overall.
  const data = {
    results: [
      { rule_id: "A.AAA.1.1", verdict: "Pass" },
      { rule_id: "B.BBB.1.1", verdict: "Fail" },
    ],
  };
  const result = eng.computeScores(data, {}, { aaa: 1 }, new Set(), 1);
  assert.strictEqual(result.overall_score, 100);
  // bbb still gets its own per-service score, it's just not rolled up.
  assert.strictEqual(result.per_service.bbb.score, 0);
});

test("M365 Results->Controls shape is ingested and attributed by service key", () => {
  // The Results KEY (uppercase "AAD" in real ScubaGear exports) becomes the
  // service and must be lowercased to match the preset key "aad".
  const data = {
    Results: {
      AAD: [
        { Controls: [
          { "Control ID": "MS.AAD.1.1v1", "Result": "Pass" },
          { "Control ID": "MS.AAD.2.1v1", "Result": "Fail" },
        ] },
      ],
    },
  };
  const result = eng.computeScores(data, {}, { aad: 1 }, new Set(), 1);
  assert.strictEqual(result.per_service.aad.score, 50);
});

test("data quality counts unknown/error entries; NA is skipped", () => {
  const data = {
    results: [
      { rule_id: "A.AAA.1.1", verdict: "Pass" },
      { rule_id: "A.AAA.1.2", verdict: "N/A" },
      { rule_id: "A.AAA.1.3", verdict: "Warning" }, // unknown bucket
    ],
  };
  const result = eng.computeScores(data, {}, { aaa: 1 }, new Set(), 1);
  assert.strictEqual(result.data_quality.total_entries_seen, 3);
  assert.strictEqual(result.data_quality.unknown_or_error_entries, 1);
  // NA is skipped entirely, so the only scored rule is the pass -> 100.
  assert.strictEqual(result.per_service.aaa.score, 100);
});

test("topFailures ranks by effective weight and flags compensated failures", () => {
  const data = {
    results: [
      { rule_id: "A.AAA.1.1", verdict: "Fail" }, // weight 4, uncompensated
      { rule_id: "A.AAA.2.1", verdict: "Fail" }, // weight 10, compensated -> eff 5
    ],
  };
  const weights = { "A.AAA.1.1": 4, "A.AAA.2.1": 10 };
  const result = eng.computeScores(data, weights, { aaa: 1 }, new Set(["A.AAA.2.1"]), 1);
  const top = eng.topFailures(result, 5);
  assert.strictEqual(top.length, 2);
  // Compensated A.AAA.2.1 has effective weight 5, beating uncompensated 4.
  assert.strictEqual(top[0].rule, "A.AAA.2.1");
  assert.strictEqual(top[0].is_compensated, true);
  assert.strictEqual(top[0].effective_weight, 5);
  assert.strictEqual(top[1].rule, "A.AAA.1.1");
  assert.strictEqual(top[1].is_compensated, false);
});

// --- Golden test: couples intentionally to the committed fixture + GWS preset. ---
// test_scuba_results.json is the small synthetic fixture at the repo root that
// the README tells users to drag in: 5 rules across gmail (1 pass / 1 fail),
// drive (2 pass), and calendar (1 fail). Its rule IDs are lowercase
// ("gws.gmail.1"), so the uppercase prefix rule weights below never match and
// every rule resolves to the default weight of 1. Per service that gives
// gmail = 50, drive = 100, calendar = 0.
//
// The overall is 25, not the (drive-inclusive) 50, because of a known quirk
// tracked in https://github.com/schmug/scubascore/issues/12: the GWS service
// preset key is "drivedocs", but this fixture's service is "drive", so drive is
// absent from the service-weight set and excluded from the roll-up. Only gmail
// (50) and calendar (0) count → (50 + 0) / 2 = 25.
//
// The weights below are copied from index.html's SERVICE_PRESETS.gws /
// DEFAULT_RULE_WEIGHTS. If you change those constants — or fix issue #12 — update
// the expected values here.
test("characterization: fixture scores 25 today due to drive/drivedocs mismatch (#12) — update when #12 is fixed", () => {
  const sample = JSON.parse(
    fs.readFileSync(path.join(REPO_ROOT, "test_scuba_results.json"), "utf8")
  );
  const GWS_SERVICE_WEIGHTS = {
    aad: 1, exo: 1, defender: 1, sharepoint: 1, teams: 1,
    gmail: 1, commoncontrols: 1, drivedocs: 1, calendar: 1,
  };
  const DEFAULT_RULE_WEIGHTS = {
    "MS.AAD.": 1.5, "MS.AAD.1.1v1": 3, "MS.AAD.3.1v1": 3, "MS.AAD.3.2v1": 2.5, "MS.AAD.3.3v1": 2,
    "MS.EXO.": 1.2, "MS.EXO.1.1v1": 2, "MS.EXO.2.2v1": 2.5, "MS.EXO.4.1v1": 2,
    "MS.DEFENDER.": 1.3, "MS.DEFENDER.1.1v1": 2, "MS.SHAREPOINT.": 1,
    "MS.TEAMS.": 1.1, "MS.TEAMS.2.1v1": 1.5,
    "GWS.GMAIL.": 1.2, "GWS.GMAIL.1.1v1": 2, "GWS.COMMONCONTROLS.": 1.4,
    "GWS.COMMONCONTROLS.1.1v1": 2.5, "GWS.DRIVEDOCS.": 1, "GWS.CALENDAR.": 0.8,
  };
  const result = eng.computeScores(sample, DEFAULT_RULE_WEIGHTS, GWS_SERVICE_WEIGHTS, new Set(), 1);
  assert.strictEqual(result.per_service.gmail.score, 50);
  assert.strictEqual(result.per_service.calendar.score, 0);

  // BUG (https://github.com/schmug/scubascore/issues/12): drive scores a perfect
  // 100 but is dropped from the overall because the GWS preset key is "drivedocs"
  // while this fixture's (and real ScubaGoggles') service is "drive". This is
  // WRONG behavior captured as-is; when #12 is fixed, drive should be included
  // and the overall should rise from 25 to 50 — update the two assertions below.
  assert.strictEqual(result.per_service.drive.score, 100, "drive is scored per-service even though it's excluded from the roll-up");
  assert.strictEqual(result.overall_score, 25, "only gmail (50) + calendar (0) count; drive dropped — see #12");

  assert.strictEqual(result.data_quality.total_entries_seen, 5);
  assert.strictEqual(result.data_quality.unknown_or_error_entries, 0);
});
