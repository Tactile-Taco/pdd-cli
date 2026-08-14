"""pdd configuration: registry endpoint resolution and workspace discovery.

Registry URL resolution order (B-005): $PDD_REGISTRY > config file > default.
The default points at the M6 pdd-registry instance (tailnet-only).
Secrets (PDD_EVIDENCE_KEY, PDD_PUBLISH_TOKEN) stay environment variables —
never stored in the config file (B-002).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Tailnet node name: MagicDNS resolves it on the tailnet and it carries a
# publicly-trusted tailscale cert (the ingress no longer uses the Traefik
# default cert or a non-resolving virtual hostname).
DEFAULT_REGISTRY = "https://staging.tail4904d2.ts.net"


def config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "pdd"


def config_path() -> Path:
    return config_dir() / "config.json"


def _read_config() -> dict:
    p = config_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _source() -> str:
    if os.environ.get("PDD_REGISTRY"):
        return "env"
    if config_path().exists():
        return "config-file"
    return "default"


def registry_url() -> str:
    """Resolution order: $PDD_REGISTRY > config file > baked default."""
    env = os.environ.get("PDD_REGISTRY")
    if env:
        return env
    return _read_config().get("registry") or DEFAULT_REGISTRY


def set_registry(url: str) -> None:
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise ValueError(f"registry URL must start with http(s)://, got {url!r}")
    data = _read_config()
    data["registry"] = url
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")


def show() -> dict:
    return {
        "registry": registry_url(),
        "registry_source": _source(),
        "config_file": str(config_path()),
    }


def workspace_root(start: Path | None = None) -> Path:
    """Nearest ancestor of `start` (default: cwd) containing pdd-bundles/."""
    cur = (start or Path.cwd()).resolve()
    for anc in (cur, *cur.parents):
        if (anc / "pdd-bundles").is_dir():
            return anc
    raise FileNotFoundError(
        "no workspace found: no pdd-bundles/ directory in the current tree "
        "(run inside a workspace or pass --workspace)")


def evidence_root(workspace: Path) -> Path:
    return workspace / "evidence"
