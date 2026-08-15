"""pdd workflow assembly — composition instances (lockfiles).

  verify <lockfile> [--bundles <root>]      structural + optional bundle-aware checks
  derive <lockfile> --protocols P1,P2,... [-o <out>] [--bundles <root>]

Assemblies are DERIVED, never adopted (registry-client ADOPTION rule): a new
project computes its own scoped lockfile from a validated assembly by keeping
its wanted protocols plus their provider closure (read from the stitch graph),
dropping the rest, and re-verifying the subgraph. The source assembly's
validated state covers the subset: kept stitches are a subgraph of a verified
composition.

Verify checks (structural, no bundles needed):
  1. environment is a map; stitches is a non-empty list
  2. consumer/provider are <bundle>@<impl>; seam is <bundle>.<capability>
  3. seam's bundle prefix equals the provider's bundle (no mismatched seam)
  4. no self-stitch (consumer bundle == provider bundle)
  5. no duplicate (consumer, seam) binding — every seam stitched exactly once
  6. stitch graph is acyclic (consumer bundle -> provider bundle)

With --bundles <root> (bundle-aware):
  7. every seam name resolves to a seam declared in the provider bundle
  8. host classes: every inline seam's host.class must be satisfiable by an
     environment platform (browser-dom -> *browser*, node-runtime ->
     *server*, storage -> *storage* — key keyword match, documented heuristic)

Exit 0 = pass, 1 = fail, 2 = usage. Network-free (B-004).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ENV_HOST_KEYWORDS = {
    "browser-dom": ("browser",),
    "node-runtime": ("server", "node"),
    "storage": ("storage", "db", "database"),
}


def _require_yaml() -> None:
    if yaml is None:
        print("error: PyYAML required (pip install pyyaml)", file=sys.stderr)
        sys.exit(1)


def _bundle_of(ref: str) -> str:
    return ref.split("@", 1)[0].split("/", 1)[0].strip()


def _load_lock(path: Path) -> dict:
    _require_yaml()
    try:
        data = yaml.safe_load(path.read_text())
    except OSError as e:
        print(f"error: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(data, dict):
        print(f"FAIL: {path}: lockfile must be a YAML map", file=sys.stderr)
        return {}
    return data


def _check_structural(data: dict, src: str) -> list[str]:
    errs = []
    env = data.get("environment")
    if not isinstance(env, dict) or not env:
        errs.append("environment: non-empty map of platform -> {…} required")
    stitches = data.get("stitches")
    if not isinstance(stitches, list) or not stitches:
        errs.append("stitches: non-empty list of {consumer, seam, provider} required")
        return errs
    seen = set()
    edges = []
    for i, s in enumerate(stitches):
        if not isinstance(s, dict):
            errs.append(f"stitch[{i}]: must be a map")
            continue
        consumer = s.get("consumer")
        seam = s.get("seam")
        provider = s.get("provider")
        if not all(isinstance(x, str) and x for x in (consumer, seam, provider)):
            errs.append(f"stitch[{i}]: consumer/seam/provider must be non-empty strings")
            continue
        cb, pb = _bundle_of(consumer), _bundle_of(provider)
        sp = seam.split(".", 1)[0]
        if sp != pb:
            errs.append(f"stitch[{i}]: seam {seam!r} names bundle {sp!r} but provider is {pb!r}")
        if cb == pb:
            errs.append(f"stitch[{i}]: self-stitch ({consumer} -> {seam})")
        key = (cb, seam)
        if key in seen:
            errs.append(f"stitch[{i}]: duplicate binding ({consumer}, {seam})")
        seen.add(key)
        edges.append((cb, pb))

    # acyclicity over (consumer bundle -> provider bundle)
    for start in {e[0] for e in edges}:
        stack, path = [(start, [start])], set()
        while stack:
            node, trail = stack.pop()
            if node in trail[:-1]:
                cyc = " -> ".join(trail[trail.index(node):] + [node])
                errs.append(f"cycle in stitch graph: {cyc}")
                break
            for (c, p) in edges:
                if c == node:
                    stack.append((p, trail + [p]))
    return errs


def _bundle_seams(bundles_root: Path, bundle: str) -> dict:
    """{seam_name: {kind, host.class}} from <root>/<bundle>/protocol.yaml."""
    _require_yaml()
    pf = bundles_root / bundle / "protocol.yaml"
    if not pf.exists():
        return {}
    try:
        data = yaml.safe_load(pf.read_text())
    except (OSError, yaml.YAMLError):
        return {}
    return data.get("seams") or {}


def _check_bundle_aware(data: dict, bundles_root: Path) -> list[str]:
    errs = []
    env = data.get("environment") or {}
    env_keys = [k.lower() for k in env]
    for i, s in enumerate(data.get("stitches") or []):
        if not isinstance(s, dict):
            continue
        provider = s.get("provider")
        seam = s.get("seam")
        if not provider or not seam:
            continue
        pb = _bundle_of(provider)
        seam_name = seam.split(".", 1)[1] if "." in seam else seam
        seams = _bundle_seams(bundles_root, pb)
        if seam_name not in seams:
            errs.append(f"stitch[{i}]: seam {seam!r} not declared by bundle {pb!r} (bundle seams: {sorted(seams) or 'none'})")
            continue
        host = seams[seam_name].get("host") if isinstance(seams[seam_name], dict) else None
        hclass = (host or {}).get("class") if isinstance(host, dict) else None
        if hclass:
            kws = ENV_HOST_KEYWORDS.get(hclass)
            if kws and not any(kw in k for k in env_keys for kw in kws):
                errs.append(
                    f"stitch[{i}]: seam {seam!r} needs host class {hclass!r} "
                    f"but no environment platform satisfies it ({env_keys})")
    return errs


def verify(lock_path: Path, bundles_root: Path | None) -> int:
    data = _load_lock(lock_path)
    errs = _check_structural(data, str(lock_path))
    if bundles_root is not None:
        errs += _check_bundle_aware(data, bundles_root)
    for e in errs:
        print(f"FAIL: {e}")
    if not errs:
        n = len(data.get("stitches") or [])
        print(f"PASS: {lock_path.name} assembly ({n} stitches, acyclic, seams resolved"
              + (", bundle-aware" if bundles_root is not None else "") + ")")
    return 1 if errs else 0


def derive(lock_path: Path, wanted: list[str], out: Path, bundles_root: Path | None) -> int:
    data = _load_lock(lock_path)
    errs = _check_structural(data, str(lock_path))
    if errs:
        for e in errs:
            print(f"FAIL (source assembly invalid): {e}")
        return 1
    stitches = data["stitches"]
    all_bundles = {_bundle_of(s["consumer"]) for s in stitches} | \
                  {_bundle_of(s["provider"]) for s in stitches}
    unknown = [w for w in wanted if w not in all_bundles]
    if unknown:
        print(f"FAIL: requested protocol(s) not composed in this assembly: {unknown}", file=sys.stderr)
        return 1

    # closure: wanted ∪ providers reachable from wanted consumers (transitive)
    kept = set(wanted)
    changed = True
    while changed:
        changed = False
        for s in stitches:
            if _bundle_of(s["consumer"]) in kept and _bundle_of(s["provider"]) not in kept:
                kept.add(_bundle_of(s["provider"]))
                changed = True

    filtered = [s for s in stitches
                if _bundle_of(s["consumer"]) in kept and _bundle_of(s["provider"]) in kept]

    derived = {"environment": data.get("environment") or {},
               "stitches": filtered,
               "derived_from": str(lock_path),
               "derived_protocols": sorted(kept),
               "derived_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    errs = _check_structural(derived, "derived assembly")
    if bundles_root is not None:
        errs += _check_bundle_aware(derived, bundles_root)
    if errs:
        for e in errs:
            print(f"FAIL (derived assembly): {e}")
        return 1

    _require_yaml()
    header = (f"# derived from {lock_path} — protocols kept: {', '.join(sorted(kept))}\n"
              "# derived, never adopted: re-verify against the registry before use.\n")
    out.write_text(header + yaml.safe_dump(derived, sort_keys=False))
    print(f"PASS: derived assembly ({len(filtered)} stitches, {len(kept)} protocols) -> {out}")
    return 0


def dispatch(argv: list[str]) -> int:
    if not argv:
        print("usage error: pdd workflow assembly requires a subcommand (verify|derive)",
              file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "verify":
        if not rest:
            print("usage error: pdd workflow assembly verify <lockfile> [--bundles <root>]",
                  file=sys.stderr)
            return 2
        lock = Path(rest[0])
        bundles_root = None
        if "--bundles" in rest:
            idx = rest.index("--bundles")
            if idx + 1 >= len(rest):
                print("usage error: --bundles requires a value", file=sys.stderr)
                return 2
            bundles_root = Path(rest[idx + 1])
        if not lock.exists():
            print(f"error: no such lockfile {lock}", file=sys.stderr)
            return 2
        return verify(lock, bundles_root)
    if cmd == "derive":
        lock = None
        wanted = []
        out = None
        bundles_root = None
        i = 0
        while i < len(rest):
            a = rest[i]
            if a == "--protocols" and i + 1 < len(rest):
                wanted = [p.strip() for p in rest[i + 1].split(",") if p.strip()]
                i += 2
            elif a == "-o" and i + 1 < len(rest):
                out = Path(rest[i + 1])
                i += 2
            elif a == "--bundles" and i + 1 < len(rest):
                bundles_root = Path(rest[i + 1])
                i += 2
            elif lock is None:
                lock = Path(a)
                i += 1
            else:
                print(f"usage error: unknown argument {a!r}", file=sys.stderr)
                return 2
        if lock is None or not wanted:
            print("usage error: pdd workflow assembly derive <lockfile> --protocols P1,P2 [-o out] [--bundles root]",
                  file=sys.stderr)
            return 2
        if not lock.exists():
            print(f"error: no such lockfile {lock}", file=sys.stderr)
            return 2
        if out is None:
            out = lock.with_name(lock.stem + "-derived.lock")
        return derive(lock, wanted, out, bundles_root)
    print(f"usage error: unknown assembly subcommand {cmd!r}", file=sys.stderr)
    return 2
