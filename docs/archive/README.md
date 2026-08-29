# Archive — superseded release notes

These files are kept for reference only. **They are not maintained.**

Release notes live in one place now:

**https://github.com/Schimmilab/oura-mcp-server/releases**

## Why they moved

The project had three parallel places for the same information, and two of them
had quietly fallen behind:

| Where | Covered | Last touched |
|---|---|---|
| GitHub Releases | v0.2.0 – current | every release |
| `releases/*.md` | up to v0.6.0 only | 2026-01-18 |
| `docs/RELEASE_NOTES.md` | **v0.2.0 only** | 2025-12-25 |

The README advertised `docs/RELEASE_NOTES.md` as "Version history and changelog"
while it contained a single release from eight months earlier. Anyone following
that link stopped looking — which is the expensive part of a stale pointer, not
the staleness itself.

Keeping one source removes three manual steps per release and the drift that
comes with them. `gh release create` writes the notes anyway.
