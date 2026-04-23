"""Valkey MCP 도구."""

from __future__ import annotations

import json
import logging

from tools import mcp
from tools.helpers import log_tool_call

logger = logging.getLogger("db-perf-mcp")


@mcp.tool()
@log_tool_call
async def valkey_execute_command(db_name: str, commands: list[list[str]]) -> str:
    """Execute one or more commands on a Valkey instance. Each command is a list of strings, e.g. [["GET", "key"], ["SET", "key", "value"]]."""
    from tools import pool_mgr
    client = await pool_mgr.valkey_client(db_name)
    results = []
    for cmd in commands:
        try:
            result = await client.execute_command(*cmd)
            results.append(result)
        except Exception as e:
            results.append(f"error: {e}")
    return json.dumps(results, default=str)
