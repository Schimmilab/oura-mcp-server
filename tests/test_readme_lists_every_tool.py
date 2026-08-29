"""The README must name every tool the server registers.

Not a style rule. The README's feature list had drifted three minor versions
behind: 29 of 30 tools were not mentioned anywhere, the roadmap stopped at
v0.6.0, and it still claimed "100% test coverage" while the suite was running
zero tests. Nobody noticed, because nothing checks documentation.

This is the mechanism instead of the good intention: add a tool without
documenting it and the suite says so.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _registered_tools() -> set[str]:
    src = (ROOT / "src" / "oura_mcp" / "core" / "server.py").read_text()
    return set(re.findall(r'name="([a-z_][a-z0-9_]*)"', src))


def test_every_registered_tool_appears_in_the_readme():
    readme = (ROOT / "README.md").read_text()
    missing = sorted(t for t in _registered_tools() if t not in readme)
    assert not missing, (
        f"{len(missing)} tool(s) registered but undocumented: {missing}\n"
        "Add them to the Features tables in README.md."
    )


def test_the_check_actually_finds_something():
    """Positive control: an empty README must fail the check above.

    Without this, a broken extraction would make the test pass by finding no
    tools at all — which is exactly how a silent check looks.
    """
    tools = _registered_tools()
    assert tools, "no tools extracted — the regex no longer matches server.py"
    assert sorted(t for t in tools if t not in ""), "extraction produced nothing to check"
