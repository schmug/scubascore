# Contributing to ScubaScore

Thanks for your interest in improving ScubaScore! This is a small project with a
deliberately narrow shape, so a little context up front will save everyone time.

## The one rule that shapes everything

ScubaScore is a **single, self-contained `index.html`** that runs **100%
client-side**. There is no server, no build step, and no bundler. Any change has
to preserve three guarantees:

1. **One file.** The UI, the scoring engine, and the default presets all live in
   `index.html`. Don't split the app into multiple shipped files or add a build
   pipeline that produces `index.html` from sources.
2. **No network egress.** The page sets a strict Content-Security-Policy
   (`connect-src 'none'`). Don't add `fetch`/`XHR`/WebSocket calls, external
   script/style/font/image URLs, or anything that would require loosening the
   CSP. Assessment data must never be able to leave the page.
3. **No untrusted HTML injection.** Because everything is inline, the CSP allows
   `'unsafe-inline'` and therefore does **not** stop script execution. The XSS
   defense is a code convention: untrusted input (file names, JSON contents) is
   only ever put into the DOM as **text** (`textContent`, `createElement`,
   `appendChild`), **never** via `innerHTML`/`outerHTML`/`insertAdjacentHTML`.

If you have a good reason to touch any of these, say so explicitly in your PR so
we can discuss it.

## Project layout

- `index.html` — the entire app. The pure, DOM-free scoring functions live in a
  region delimited by `// === SCORING ENGINE START ===` and
  `// === SCORING ENGINE END ===`, which ends with a `module.exports` line so the
  engine can be `require`d under Node for testing.
- `test/score.test.cjs` — the test suite (see below).
- `test_scuba_results.json` — a small sample fixture the README tells users to
  drag in; also used by the tests.
- `.github/` — issue forms, PR template, and the CI workflow.

## Development

There is nothing to install — the app is just a file.

- **Run the app:** open `index.html` in any modern browser (double-click it or
  drag it onto a window). No web server required.
- **Run the tests:** you need Node ≥ 18 (for the built-in test runner), but **no
  `npm install`** — there are no runtime or dev dependencies.

  ```sh
  npm test        # or: node --test
  ```

The test suite extracts the scoring engine from the shipped `index.html` at
runtime (it slices between the `SCORING ENGINE` markers, writes a temp `.cjs`,
and `require`s it), so it verifies the file users actually load. **It never forks
the scoring logic into a second source file** — `index.html` stays the single
source of truth.

If you change the scoring engine, **add or update tests in `test/`**. If you
change `SERVICE_PRESETS` or `DEFAULT_RULE_WEIGHTS`, update the characterization
test's expected values (the test has a comment pointing at exactly what to
change).

## Submitting changes

1. **Open an issue first** for anything non-trivial, using the bug or feature
   templates, so we can agree on the approach before you build it.
2. **Branch** off `main` and keep your change focused.
3. **Run `npm test`** and make sure it passes.
4. **Use conventional commit prefixes** — `feat:`, `fix:`, `docs:`, `refactor:`,
   `test:`, `chore:`, `security:`. This keeps history readable and the changelog
   easy to assemble.
5. **Open a pull request** and fill out the checklist in the PR template.
6. **Update the docs** (`README.md`, `CHANGELOG.md`) when your change is
   user-visible.

## Reporting security issues

Please **do not** open a public issue for a vulnerability. See
[`SECURITY.md`](SECURITY.md) for how to report privately.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By
participating, you agree to uphold it.
