# ScubaScore

Score CISA SCuBA assessment output — **entirely in your browser**.

ScubaScore is a single, self-contained `index.html` that turns the JSON
produced by CISA's [ScubaGoggles](https://github.com/cisagov/ScubaGoggles)
(Google Workspace) and [ScubaGear](https://github.com/cisagov/ScubaGear)
(Microsoft 365) tools into a quantified compliance score. There is no server,
no install step, and no build. Your assessment data is parsed locally and
never leaves the machine.

## What it is

- **One file.** Everything — the UI, the scoring engine, and the default
  weight presets — lives in `index.html`. Copy that one file anywhere and it
  works.
- **100% client-side.** All parsing and scoring happen in the browser. No
  network requests are made with your data.
- **Customizable risk model.** Per-rule weights, per-service weights, and
  compensating-control credit are all editable, with sensible presets for
  Google Workspace (GWS) and Microsoft 365 (M365).

## How to use

1. **Open `index.html` in any modern browser** — double-click the file, or
   drag it onto a browser window. No web server required.
2. **Load your assessment JSON.** On the **Results** tab, drag and drop one or
   more ScubaGoggles / ScubaGear `.json` files onto the drop zone, or click it
   to pick files. Multiple files are allowed; each gets its own scorecard.
3. **Read the scores.** Results render instantly. Adjust the model on the
   **Weights** tab and every loaded file rescores live.

Want to try it first? Load the bundled **`test_scuba_results.json`** sample to
see a full scorecard with passes, failures, and a compensating control.

## Results shown

For each loaded file, ScubaScore displays:

- **Overall score** — a single weighted percentage (0–100) with a color band:
  green (≥ 80), amber (≥ 50), or red (below 50).
- **Per-service breakdown** — score, passed/failed counts, and evaluated
  weight for each service (e.g. `aad`, `exo`, `gmail`, `drivedocs`).
- **Top failures** — the highest-impact failed rules across all services,
  ranked by effective weight, with compensated failures flagged.
- **Data quality** — a count of unknown or unreadable entries out of the total
  entries seen, so you know how much of the input was actually scored.

Files that aren't valid JSON are reported inline without blocking the rest.

## Custom weights

The **Weights** tab is a full editor for the scoring model. Everything you
change is applied immediately and persisted automatically.

- **Service weights** — the multiplier each service contributes to the overall
  roll-up. A service listed here counts toward the overall score; a service
  absent from the list still shows its own per-service score but is excluded
  from the overall.
- **Rule weights** — the base weight for individual rules. Keys ending in `.`
  are treated as **prefix** rules (longest-prefix match); all other keys are
  exact rule IDs. Anything unmatched falls back to the editable default rule
  weight.
- **Compensating controls** — a list of rule IDs that earn partial credit when
  they fail (see the scoring model below).
- **Presets** — one-click **GWS** and **M365** weight sets. Editing any weight
  switches the active set to **Custom**.
- **Auto-save** — your weights persist in the browser's `localStorage`, so they
  survive reloads on the same machine and browser.
- **Export / Import** — download the current weights as a JSON file, or import
  a previously saved one to move your configuration between machines.
- **Reset to preset** — restore the canonical GWS or M365 weights at any time.

## Scoring model

ScubaScore converts pass/fail verdicts into a weighted percentage:

1. **Per-rule weight resolution.** Each rule's weight is resolved in order:
   **exact** rule-ID match → **longest-prefix** match (keys ending in `.`) →
   the **default** rule weight.
2. **Compensating credit.** A failed rule listed as a compensating control
   contributes **50%** of its weight to the numerator while keeping its full
   weight in the denominator. Other failures contribute 0%. Rules marked `NA`
   are skipped entirely.
3. **Per-service percentage.** For each service,
   `score = passed_weight / evaluated_weight × 100`.
4. **Service-weighted overall.** The overall score is the average of
   per-service scores weighted by each service's configured weight. Only
   services that are present in the service weights and have a non-null score
   are counted.

## Privacy

ScubaScore is designed to be safe to run against sensitive compliance data:

- **100% client-side** — parsing and scoring happen entirely in your browser.
- **Nothing is uploaded** — no data is sent to any server or third party. A
  strict Content-Security-Policy blocks outbound connections.
- **Offline-capable** — once you have `index.html`, it works with no network
  connection at all.

The only thing stored anywhere is your custom weight configuration, which is
saved locally in your browser's `localStorage`.

## License

See repository for license details.
