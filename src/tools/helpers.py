"""공통 쿼리 실행 헬퍼. 도구명 로깅 포함."""

from __future__ import annotations

import json
import logging
import functools
from typing import Callable

import aiomysql

logger = logging.getLogger("db-perf-mcp")


def _get_pool_mgr():
    """순환 import 방지를 위해 지연 로딩."""
    from tools import pool_mgr
    return pool_mgr


async def pg_query(db_name: str, query: str, params: list | None = None, database: str | None = None, timeout: float | None = None) -> str:
    """PostgreSQL 쿼리를 실행하고 JSON 문자열로 반환."""
    pool = await _get_pool_mgr().pg_pool(db_name, database=database)
    if timeout:
        async with pool.acquire() as conn:
            await conn.execute(f"SET statement_timeout = '{int(timeout * 1000)}'")
            try:
                rows = await conn.fetch(query, *(params or []))
            finally:
                await conn.execute("RESET statement_timeout")
    else:
        rows = await pool.fetch(query, *(params or []))
    return json.dumps([dict(r) for r in rows], default=str)


async def mysql_query(db_name: str, query: str, params: tuple | None = None, timeout: float | None = None) -> str:
    """MySQL 쿼리를 실행하고 JSON 문자열로 반환."""
    pool = await _get_pool_mgr().mysql_pool(db_name)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            if timeout:
                await cur.execute(f"SET max_execution_time = {int(timeout * 1000)}")
            await cur.execute(query, params)
            rows = await cur.fetchall()
            if timeout:
                await cur.execute("SET max_execution_time = 0")
    return json.dumps(rows, default=str)


def log_tool_call(func: Callable) -> Callable:
    """도구 호출 시 도구명, 인자값, 결과 크기를 로깅하는 데코레이터."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> str:
        tool_name = func.__name__
        # 인자값 포맷팅
        args_str = ", ".join(repr(a) for a in args)
        kwargs_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        all_args = ", ".join(filter(None, [args_str, kwargs_str]))
        
        logger.info("[%s] 호출: %s", tool_name, all_args)
        try:
            result = await func(*args, **kwargs)
            logger.info("[%s] 완료: %d bytes", tool_name, len(result))
            return result
        except Exception as e:
            logger.error("[%s] 에러: %s", tool_name, e)
            return json.dumps({"error": str(e)})

    return wrapper
