"""pdd workflow evidence — signed evidence build, ledger verify, packaging.

Port of the pdd-registry evidence build/verify with the evidence root
parameterized (workspace/evidence by default). Byte-compatible with the
original: the same candidate digest, discovery binding, ledger append, and
verify semantics.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path

from .. import config as cfg
from .. import engine
from .. import evidence as ev


def _evidence_root(bundle: Path, argv: list[str]) -> Path:
    if "--evidence-dir" in argv:
        idx = argv.index("--evidence-dir")
        if idx + 1 >= len(argv):
            sys.exit("usage error: --evidence-dir requires a value")
        return Path(argv[idx + 1]).resolve()
    try:
        ws = cfg.workspace_root(bundle)
        return cfg.evidence_root(ws)
    except FileNotFoundError:
        return bundle.parent / "evidence"


def dispatch(argv: list[str]) -> int:
    if not argv:
        print("usage error: pdd workflow evidence build|verify|package", file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "build":
        return build(rest)
    if cmd == "verify":
        return verify(rest)
    if cmd == "package":
        return package(rest)
    print(f"usage error: unknown evidence subcommand {cmd!r}", file=sys.stderr)
    return 2


def _bundle(argv: list[str], what: str) -> Path:
    if not argv:
        print(f"usage error: pdd workflow evidence {what} <bundle-dir>", file=sys.stderr)
        sys.exit(2)
    b = Path(argv[0]).resolve()
    if not b.is_dir() or not (b / "protocol.yaml").exists():
        sys.exit(f"error: no bundle at {b}")
    return b


def build(argv: list[str]) -> int:
    bundle = _bundle(argv, "build")
    if "--impl" not in argv:
        print("usage error: evidence build requires --impl <impl-dir>", file=sys.stderr)
        return 2
    impl = Path(argv[argv.index("--impl") + 1]).resolve()
    validation_resource = None
    if "--validation-resource" in argv:
        validation_resource = argv[argv.index("--validation-resource") + 1]
    ev_root = _evidence_root(bundle, argv)
    name = bundle.name
    manifest = json.loads((impl / "candidate-manifest.json").read_text())
    entry_module = manifest.get("entry_module")
    if not entry_module:
        sys.exit("candidate-manifest.json must declare `entry_module`")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", entry_module):
        sys.exit(f"entry_module must be a Python identifier, got {entry_module!r}")
    impl_digest = engine.candidate_digest(impl, entry_module)
    proto = engine.load_yaml(bundle / "protocol.yaml") or {}
    protocol = proto.get("protocol") or proto
    version = protocol.get("version") or "1.0.0"
    results_file = next(
        (ev_root / name / "validation").glob(f"{impl_digest.split(':')[1][:12]}*.results.json"),
        None)
    if results_file is None:
        sys.exit("no validation results for this candidate digest — run `pdd workflow validate` first")
    results = json.loads(results_file.read_text())
    if results.get("candidate_digest") != impl_digest:
        sys.exit(f"candidate digest mismatch: results attest {results.get('candidate_digest')}, "
                 f"--impl is {impl_digest}; refusing to bind evidence to the wrong artifact")
    if results["verdict"] != "admit":
        sys.exit(f"cannot build admission evidence: verdict is {results['verdict']}")

    # Idempotency: an admission that is already attested keeps its attested
    # evidence snapshot (provenance time is part of the signed body, so a
    # rebuild would overwrite the attested object and force a new block).
    ledger = ev_root / name / "runtime-ledger.jsonl"
    if ledger.exists():
        existing = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
        matches = [b for b in existing
                   if (b.get("observations") or {}).get("admission") == impl_digest]
        if matches:
            attested_digest = (matches[-1].get("observations") or {}).get("evidence_digest")
            adm_file = next(
                (ev_root / name / "admission").glob(f"{impl_digest.split(':')[1][:16]}*.evidence.json"),
                None)
            if adm_file is None or not attested_digest:
                print(f"FAIL: admission {impl_digest.split(':')[1][:16]} is attested "
                      f"but its evidence file is missing from disk")
                return 1
            on_disk = "sha256:" + hashlib.sha256(adm_file.read_bytes()).hexdigest()
            if on_disk != attested_digest:
                print(f"FAIL: attested evidence file differs from the ledger "
                      f"(on disk {on_disk} != attested {attested_digest}) — re-run validate, then rebuild")
                return 1
            print(f"admission {impl_digest.split(':')[1][:16]} already attested and consistent; "
                  f"evidence snapshot preserved (re-verify with `pdd workflow evidence verify`)")
            return 0

    evidence = {
        "protocol": {"name": name, "version": version,
                     "bundle_digest": results["protocol"]["bundle_digest"]},
        "implementation": {"artifact_id": manifest["artifact_id"],
                           "artifact_digest": impl_digest,
                           "language": manifest["language"],
                           "runtime": manifest["runtime"]},
        "validators": results["validators"],
        "results": results["results"],
        "discovery_log": {
            "files": manifest["files"],
            "dependencies": manifest["dependencies"],
            "invariant_lineage": manifest["invariant_lineage"],
            "known_limitations": manifest["known_limitations"],
        },
        "decision": "admit",
    }
    if validation_resource:
        evidence["validation_resource"] = validation_resource
    disc = ev_root / name / "discovery"
    disc.mkdir(parents=True, exist_ok=True)
    disc_path = disc / f"{impl_digest.split(':')[1][:16]}.discovery.json"
    disc_path.write_text(json.dumps(evidence["discovery_log"], indent=2))
    disc_digest = "sha256:" + hashlib.sha256(disc_path.read_bytes()).hexdigest()
    meta = {"manifest": manifest["artifact_id"], "discovery_digest": disc_digest}
    if validation_resource:
        # Signed inside the provenance block — mutating the object AFTER
        # signing would invalidate the digest (S-001/evidence contract).
        meta["validation_resource"] = validation_resource
    evidence_obj = ev.build_evidence(
        evidence["protocol"], impl_digest, results["validators"], results["results"], meta)

    adm = ev_root / name / "admission"
    adm.mkdir(parents=True, exist_ok=True)
    evidence_path = adm / f"{impl_digest.split(':')[1][:16]}.evidence.json"
    evidence_path.write_text(json.dumps(evidence_obj, indent=2))
    evidence_digest = "sha256:" + hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    ev.append_block(
        ledger, json.dumps({"id": name, "version": version}),
        manifest["artifact_id"] + "@" + impl_digest.split(':')[1][:12],
        {"admission": impl_digest, "evidence_digest": evidence_digest},
        "attest-pass")
    print(f"evidence built: admission/{impl_digest.split(':')[1][:16]}.evidence.json")
    print(f"genesis block appended to {ledger}")
    return 0


def verify(argv: list[str]) -> int:
    bundle = _bundle(argv, "verify")
    ev_root = _evidence_root(bundle, argv)
    name = bundle.name
    ledger = ev_root / name / "runtime-ledger.jsonl"
    if not ledger.exists():
        sys.exit(f"no ledger at {ledger}")
    result = ev.verify_ledger(ledger)
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        return 1
    rc = 0
    blocks = [json.loads(ln) for ln in ledger.read_text().splitlines() if ln.strip()]
    attested = {}
    for b in blocks:
        obs = b.get("observations") or {}
        if obs.get("evidence_digest"):
            attested[obs["evidence_digest"]] = b
    for path in sorted((ev_root / name / "admission").glob("*.evidence.json")):
        cur = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if cur not in attested:
            print(f"FAIL: {path.name} is not attested by the ledger (no matching evidence_digest)")
            rc = 1
            continue
        block = attested[cur]
        ev_obj = json.loads(path.read_text())
        block_admission = (block.get("observations") or {}).get("admission")
        ev_artifact = (ev_obj.get("implementation") or {}).get("artifact_digest")
        if block_admission != ev_artifact:
            print(f"FAIL: {path.name} attesting block binds admission {block_admission}, "
                  f"evidence object attests {ev_artifact}")
            rc = 1
            continue
        vres = ev.verify_evidence_object(path)
        if not vres["ok"]:
            print(f"FAIL: {path.name} digest/signature invalid ({vres['reason']})")
            rc = 1
        else:
            print(f"OK: {path.name} digest+signature valid, ledger-attested")
            disc_digest = (ev_obj.get("provenance") or {}).get("discovery_digest")
            if disc_digest:
                disc_file = next(
                    (ev_root / name / "discovery").glob(f"{path.name[:16]}*.discovery.json"), None)
                if disc_file is None:
                    print("FAIL: evidence binds a discovery digest but no discovery file on disk")
                    rc = 1
                else:
                    on_disk = "sha256:" + hashlib.sha256(disc_file.read_bytes()).hexdigest()
                    if on_disk != disc_digest:
                        print(f"FAIL: discovery file digest mismatch (signed {disc_digest}, on disk {on_disk})")
                        rc = 1
    if not attested:
        print("FAIL: ledger contains no evidence attestation blocks (nothing verified)")
        rc = 1
    return rc


def package(argv: list[str]) -> int:
    bundle = _bundle(argv, "package")
    out = None
    if "-o" in argv:
        out = argv[argv.index("-o") + 1]
    if not out:
        print("usage error: pdd workflow evidence package <bundle-dir> -o <out-file>", file=sys.stderr)
        return 2
    ev_root = _evidence_root(bundle, argv)
    name = bundle.name
    src = ev_root / name
    if not src.is_dir():
        sys.exit(f"no evidence for {name} at {src} — run validate and evidence build first")
    with tarfile.open(out, "w:gz") as tf:
        tf.add(src, arcname=name)
    print(f"packaged evidence for {name} -> {out}")
    return 0
