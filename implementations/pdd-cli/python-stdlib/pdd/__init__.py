"""pdd — Protocol-Driven Development CLI.

Two namespaces:
  pdd workflow ...   the author-side loop (lint, seal, validate, evidence,
                     run, staleness, status) — offline, path-based
  pdd registry ...   the pdd-registry client (search, index, inspect,
                     verify, publish) — HTTP against the configured instance

The Adapter is exported at package root (no heavy imports) so the sandbox
smoke and benchmark can `from pdd import Adapter` in a stdlib-only image.
"""

from .adapter import Adapter

__version__ = "0.1.0"
__all__ = ["Adapter", "__version__"]
