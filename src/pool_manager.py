"""DB 커넥션 풀을 관리한다. name → pool 매핑. Lazy 연결 방식."""

from __future__ import annotations

import asyncio
import logging

import asyncpg
import aiomysql
import valkey.asyncio as avalkey

from config import AppConfig, Credentials, DatabaseEntry

logger = logging.getLogger("db-perf-mcp")

_CONNECT_TIMEOUT = 10


class PoolManager:
    """타입별 커넥션 풀을 lazy하게 생성하고 name으로 조회한다."""

    def __init__(self) -> None:
        self._pg_pools: dict[str, asyncpg.Pool] = {}
        self._mysql_pools: dict[str, aiomysql.Pool] = {}
        self._valkey_clients: dict[str, avalkey.Valkey] = {}
        self._db_map: dict[str, DatabaseEntry] = {}
        self._credentials: Credentials | None = None
        self._locks: dict[str, asyncio.Lock] = {}

    async def initialize(self, config: AppConfig) -> None:
        """DB 목록만 등록하고, 실제 연결은 첫 요청 시 수행."""
        self._credentials = config.credentials
        for db in config.databases:
            self._db_map[db.name] = db
            self._locks[db.name] = asyncio.Lock()
        logger.info("DB 등록 완료: %d개 (연결은 첫 요청 시 수행)", len(self._db_map))

    async def _ensure_pg(self, name: str) -> asyncpg.Pool:
        if name in self._pg_pools:
            return self._pg_pools[name]
        async with self._locks[name]:
            if name in self._pg_pools:
                return self._pg_pools[name]
            db = self._db_map[name]
            creds = self._credentials
            pool = await asyncio.wait_for(
                asyncpg.create_pool(
                    host=db.host, port=db.port,
                    user=creds.pg_user, password=creds.pg_password,
                    database=db.database, min_size=1, max_size=5,
                ),
                timeout=_CONNECT_TIMEOUT,
            )
            self._pg_pools[name] = pool
            logger.info("PG pool 생성 (lazy): %s (%s)", name, db.host)
            return pool

    async def _ensure_pg_database(self, name: str, database: str) -> asyncpg.Pool:
        """같은 서버의 다른 database로 연결하는 풀. name:database 키로 캐싱."""
        cache_key = f"{name}:{database}"
        if cache_key in self._pg_pools:
            return self._pg_pools[cache_key]

        # DB별 lock이 없으므로 동적으로 생성
        if cache_key not in self._locks:
            self._locks[cache_key] = asyncio.Lock()

        async with self._locks[cache_key]:
            if cache_key in self._pg_pools:
                return self._pg_pools[cache_key]
            db = self._db_map[name]
            creds = self._credentials
            pool = await asyncio.wait_for(
                asyncpg.create_pool(
                    host=db.host, port=db.port,
                    user=creds.pg_user, password=creds.pg_password,
                    database=database, min_size=1, max_size=3,
                ),
                timeout=_CONNECT_TIMEOUT,
            )
            self._pg_pools[cache_key] = pool
            logger.info("PG pool 생성 (lazy, db=%s): %s (%s)", database, name, db.host)
            return pool

    async def _ensure_mysql(self, name: str) -> aiomysql.Pool:
        if name in self._mysql_pools:
            return self._mysql_pools[name]
        async with self._locks[name]:
            if name in self._mysql_pools:
                return self._mysql_pools[name]
            db = self._db_map[name]
            creds = self._credentials
            pool = await asyncio.wait_for(
                aiomysql.create_pool(
                    host=db.host, port=db.port,
                    user=creds.mysql_user, password=creds.mysql_password,
                    db=db.database, minsize=1, maxsize=5,
                    autocommit=True,
                ),
                timeout=_CONNECT_TIMEOUT,
            )
            self._mysql_pools[name] = pool
            logger.info("MySQL pool 생성 (lazy): %s (%s)", name, db.host)
            return pool

    async def _ensure_valkey(self, name: str) -> avalkey.Valkey:
        if name in self._valkey_clients:
            return self._valkey_clients[name]
        async with self._locks[name]:
            if name in self._valkey_clients:
                return self._valkey_clients[name]
            db = self._db_map[name]
            creds = self._credentials
            host, _, port_str = db.address.rpartition(":")
            client = avalkey.Valkey(
                host=host, port=int(port_str),
                username=creds.valkey_username or None,
                password=creds.valkey_password or None,
                decode_responses=True,
            )
            await asyncio.wait_for(client.ping(), timeout=_CONNECT_TIMEOUT)
            self._valkey_clients[name] = client
            logger.info("Valkey 연결 (lazy): %s (%s)", name, db.address)
            return client

    # ── 조회 (lazy 연결) ──

    async def pg_pool(self, name: str, database: str | None = None) -> asyncpg.Pool:
        db = self._db_map.get(name)
        if not db or db.type != "postgres":
            raise ValueError(f"Unknown postgres DB: {name}. Available: {[n for n, d in self._db_map.items() if d.type == 'postgres']}")
        if database and database != db.database:
            return await self._ensure_pg_database(name, database)
        return await self._ensure_pg(name)

    async def mysql_pool(self, name: str) -> aiomysql.Pool:
        db = self._db_map.get(name)
        if not db or db.type != "mysql":
            raise ValueError(f"Unknown mysql DB: {name}. Available: {[n for n, d in self._db_map.items() if d.type == 'mysql']}")
        return await self._ensure_mysql(name)

    async def valkey_client(self, name: str) -> avalkey.Valkey:
        db = self._db_map.get(name)
        if not db or db.type != "valkey":
            raise ValueError(f"Unknown valkey: {name}. Available: {[n for n, d in self._db_map.items() if d.type == 'valkey']}")
        return await self._ensure_valkey(name)

    def list_databases(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {"postgres": [], "mysql": [], "valkey": []}
        for name, db in self._db_map.items():
            if db.type in result:
                result[db.type].append(name)
        return result

    async def close(self) -> None:
        for pool in self._pg_pools.values():
            await pool.close()
        for pool in self._mysql_pools.values():
            pool.close()
            await pool.wait_closed()
        for client in self._valkey_clients.values():
            await client.aclose()
