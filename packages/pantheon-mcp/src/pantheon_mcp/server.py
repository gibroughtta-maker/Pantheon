"""Pantheon MCP server — stdio transport.

Run from the command line:
    pantheon-mcp                       # stdio MCP server, ready for client
    PANTHEON_GATEWAY=openclaw pantheon-mcp

Configure your MCP client (Claude Desktop, Cursor, Cline, Claude Code)
per the README. The server speaks the standard MCP stdio protocol; it
exposes 8 tools (see ``pantheon_mcp.tools.TOOL_SCHEMAS``) and dispatches
each call into the in-process Pantheon SDK.
"""
from __future__ import annotations

import asyncio
import json
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from pantheon_mcp.sessions import SessionManager, gateway_from_env
from pantheon_mcp.tools import TOOL_SCHEMAS, handle

log = logging.getLogger("pantheon-mcp")


def _build_server() -> tuple[Server, SessionManager]:
    """Build a Server bound to a fresh SessionManager. Exposed for tests."""
    server: Server = Server("pantheon")
    mgr = SessionManager(gateway=gateway_from_env())

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in TOOL_SCHEMAS
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict | None) -> list[TextContent]:
        try:
            result = await handle(name, arguments or {}, mgr)
        except Exception as e:  # noqa: BLE001 — surface as MCP error result text
            log.exception("tool %s failed", name)
            return [TextContent(type="text",
                                 text=json.dumps({"error": str(e), "tool": name}))]
        return [TextContent(type="text",
                             text=json.dumps(result, ensure_ascii=False))]

    return server, mgr


async def run_server() -> None:
    server, _mgr = _build_server()
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    """Entry point for the ``pantheon-mcp`` console script."""
    logging.basicConfig(level=logging.INFO,
                         format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run_server())
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("shutdown")


if __name__ == "__main__":
    main()
