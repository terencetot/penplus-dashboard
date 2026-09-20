"""qc.py is a separate, currently-unused standalone script for an older version
of the reporting form (different section numbering) and does not integrate
with parse.py/validate.py/load.py. This is only a smoke check that it still
imports cleanly, not a test of its behaviour."""
from __future__ import annotations

import importlib


def test_qc_module_imports():
    importlib.import_module("qc")
