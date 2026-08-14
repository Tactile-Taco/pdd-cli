# Ambiguity Log — pdd-cli

## Resolved Assumptions

- **The CLI is decoupled from the registry repo.** Shared tooling (linter,
  validation engine, evidence chain) lives in this package; the pdd-registry
  repo depends on the installed pdd binary/package. The registry's own
  protocol bundle and evidence chain stay in the registry repo, re-verified
  with this tool (byte-compatible evidence algorithm).
- **Evidence algorithm is byte-compatible.** canon/digest/sign and the ledger
  chain are ports of the pdd-registry evidence chain; evidence signed by
  either tool verifies with the other, with the same PDD_EVIDENCE_KEY.
- **Two namespaces, one binary.** `pdd workflow` (local, offline) and
  `pdd registry` (HTTP client) share config and the evidence code; the
  publish command is the seam that bridges them.
- **Registry endpoint default is the M6 instance** (tailnet-only). The
  resolution order is env > config file > default; a tailnet-off default
  fails closed at the network layer, never silently.
- **Engine O-layer policy is manifest-driven.** capability-manifest.yaml
  capabilities.dependencies declares the import/call allowlist and forbidden
  sets; bundles without the block keep the engine's built-in defaults
  (stdlib-only), so the pdd-registry candidate validates identically.
- **Candidate digest covers the package tree.** entry_module may name a
  package dir; the attested digest then covers the whole package, and the
  sandbox smoke exercises the adapter (config show) so the stdlib-only
  sandbox image needs no third-party deps.

## Open Questions

- Should `pdd registry publish` support remote validation submission (the
  registry currently runs no validators; author-owned validation with a
  validation_resource URL is the honor-system contract)? Pending the
  registry's own publish-endpoint protocol decision.

## Rejected Interpretations

- **AppImage/.tar releases for the CLI.** A wheel + console script is the
  standard Python distribution; Arch consumption happens via AUR wrapping the
  release artifacts. AppImage is a GUI-app format, wrong for a CLI.
- **Attesting the pdd-registry server inside this bundle.** The server is
  out of scope; it is governed by its own protocol bundle.
