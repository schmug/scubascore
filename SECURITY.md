# Security Policy

ScubaScore parses CISA SCuBA assessment output — potentially sensitive
compliance data — entirely in the browser. Its core security promise is that
**your data never leaves the page**. This policy describes how that promise is
enforced and how to report a problem if you find a way to break it.

## Supported versions

ScubaScore is a single, self-contained `index.html` with no build step or
release train. Only the current version on the `main` branch (and the copy
deployed to <https://schmug.github.io/scubascore/>) is supported. Fixes land on
`main`; there are no backported releases.

| Version | Supported |
| ------- | --------- |
| `main` / latest deploy | ✅ |
| Older copies you've saved locally | ❌ (re-download `index.html`) |

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Report privately via GitHub's
[**"Report a vulnerability"**](https://github.com/schmug/scubascore/security/advisories/new)
button on the repository's **Security** tab. This opens a private advisory only
the maintainers can see.

When reporting, please include:

- A description of the issue and why it matters.
- Steps to reproduce (a crafted input file, a sequence of UI actions, etc.).
- The browser and version you observed it in.
- The impact you believe it has (e.g. data exfiltration, script execution).

We aim to acknowledge reports within a few days. Because this is a small
volunteer project, please allow reasonable time for a fix before any public
disclosure.

## Threat model

ScubaScore's security rests on a few deliberate properties:

- **No network egress.** A strict Content-Security-Policy sets
  `connect-src 'none'`, which blocks `fetch`, `XMLHttpRequest`, WebSocket, and
  `EventSource`. Locally-parsed assessment data cannot be sent anywhere.
- **No server, no telemetry.** Everything runs client-side. The only persisted
  state is your custom weight configuration in the browser's `localStorage`.
- **No untrusted HTML injection.** Because the app is a single inline file, the
  CSP must allow `'unsafe-inline'`, so the CSP itself does **not** prevent
  script *execution*. The XSS defense is therefore a code convention: untrusted
  input (file names, JSON contents) is only ever inserted into the DOM as text
  (`textContent` / `createElement`), never via `innerHTML`.

Examples of issues that are **in scope**:

- Any way to make ScubaScore transmit loaded data off the page (a CSP bypass,
  an unexpected network request, a data-leaking redirect/download).
- Cross-site scripting — getting attacker-controlled content from a loaded file
  to execute as script.
- Weakening of the Content-Security-Policy that removes a protection above.

Examples that are typically **out of scope**:

- Findings that require a compromised browser, malicious extension, or
  attacker-controlled local machine.
- Self-XSS that requires a victim to paste attacker-supplied content into dev
  tools.
- The fact that your weight configuration is stored in `localStorage` on your
  own machine (this is by design and contains no assessment data).

Thank you for helping keep ScubaScore safe to run against real compliance data.
