"""DB Performance MCP Tools."""

from mcp.server.fastmcp import FastMCP

from pool_manager import PoolManager

mcp = FastMCP("db-perf-mcp-server")
pool_mgr = PoolManager()

# 도구 등록 (import 시 @mcp.tool() 데코레이터가 실행됨)
from tools.common import *    # noqa: F401,F403,E402
from tools.postgres import *  # noqa: F401,F403,E402
from tools.mysql import *     # noqa: F401,F403,E402
from tools.valkey import *    # noqa: F401,F403,E402

__all__ = ["mcp", "pool_mgr"]
