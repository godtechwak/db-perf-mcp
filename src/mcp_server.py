"""DB Performance Monitoring MCP Server — Entry Point."""

from __future__ import annotations

import asyncio
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("db-perf-mcp")

from config import AppConfig
from tools import mcp, pool_mgr


async def main() -> None:
    import uvicorn
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    # DB 풀 초기화 (uvicorn 이벤트 루프 내에서 실행)
    app_config = AppConfig.from_env()
    await pool_mgr.initialize(app_config)
    logger.info("Pool 초기화 완료: %s", pool_mgr.list_databases())

    os.environ["MCP_ALLOW_ALL_HOSTS"] = "true"
    app = mcp.streamable_http_app()

    class HostOverrideMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            scope = request.scope
            headers = dict(scope["headers"])
            headers[b"host"] = b"localhost:8000"
            scope["headers"] = list(headers.items())
            return await call_next(request)

    app.add_middleware(HostOverrideMiddleware)

    logger.info("Starting db-perf-mcp-server on 0.0.0.0:8000...")
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
