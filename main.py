#!/usr/bin/env python3
"""
Oura MCP Server - Entry Point

Model Context Protocol server for Oura Ring health data.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from oura_mcp.core.server import start_server


def main():
    """Main entry point."""
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
