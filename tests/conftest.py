"""Make ``src/`` importable for every test module.

Without this each test file has to prepend the path itself, and the two that
forgot (``test_api.py``, ``test_advanced_features.py``) failed at collection —
which aborted the whole run, so no test in the suite executed.
"""

import sys
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# ── Live smoke scripts, not unit tests ──────────────────────────────────────
# These three predate the suite: they are standalone `asyncio.run` scripts that
# talk to the real Oura API and need working credentials plus network. Collected
# as tests they only ever produced "async def functions are not natively
# supported" noise, which is why they are skipped here rather than fixed.
#
# Run them by hand when you want an end-to-end check against the live account:
#     python tests/test_api.py
#     python tests/test_server.py
#     python tests/test_advanced_features.py
collect_ignore = [
    "test_api.py",
    "test_server.py",
    "test_advanced_features.py",
]
