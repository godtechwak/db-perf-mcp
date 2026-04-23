"""공통 도구."""

import json

from tools import mcp


@mcp.tool()
async def list_databases() -> str:
    """List all registered database connections grouped by type."""
    from tools import pool_mgr
    return json.dumps(pool_mgr.list_databases())
