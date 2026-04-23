"""DB 서버 목록과 자격 증명을 환경변수에서 로드한다."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger("db-perf-mcp")


@dataclass(frozen=True)
class Credentials:
    pg_user: str
    pg_password: str
    mysql_user: str
    mysql_password: str
    valkey_username: str
    valkey_password: str

    @classmethod
    def from_env(cls) -> Credentials:
        return cls(
            pg_user=os.environ.get("DB_USER", ""),
            pg_password=os.environ.get("DB_PASSWORD", ""),
            mysql_user=os.environ.get("DB_USER", ""),
            mysql_password=os.environ.get("DB_PASSWORD", ""),
            valkey_username=os.environ.get("VALKEY_USERNAME", ""),
            valkey_password=os.environ.get("VALKEY_PASSWORD", ""),
        )


@dataclass(frozen=True)
class DatabaseEntry:
    name: str
    type: str  # "postgres" | "mysql" | "valkey"
    host: str
    port: int = 0
    database: str = ""
    address: str = ""
    label: str = ""

    def __post_init__(self):
        # frozen이라 object.__setattr__ 사용
        if not self.label:
            object.__setattr__(self, "label", self.name)
        if self.type == "postgres" and not self.port:
            object.__setattr__(self, "port", 5432)
        if self.type == "postgres" and not self.database:
            object.__setattr__(self, "database", "postgres")
        if self.type == "mysql" and not self.port:
            object.__setattr__(self, "port", 3306)
        if self.type == "mysql" and not self.database:
            object.__setattr__(self, "database", "information_schema")
        if self.type == "valkey" and not self.address:
            p = self.port or 6379
            object.__setattr__(self, "address", f"{self.host}:{p}")


@dataclass(frozen=True)
class AppConfig:
    credentials: Credentials
    databases: list[DatabaseEntry] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> AppConfig:
        creds = Credentials.from_env()
        raw = os.environ.get("DATABASES", "[]")
        try:
            parsed = json.loads(raw)
            # ESO가 property를 파싱해서 dict/list로 넘기는 경우 대응
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            if isinstance(parsed, dict):
                # 배열이 아닌 객체로 들어온 경우 빈 리스트 처리
                logger.warning("DATABASES가 배열이 아닌 객체로 파싱됨, 빈 리스트로 처리: %s", type(parsed))
                entries = []
            else:
                entries = parsed
        except json.JSONDecodeError as e:
            logger.error("DATABASES JSON 파싱 실패: %s (raw 길이: %d, 앞 100자: %s)", e, len(raw), raw[:100])
            entries = []

        dbs = []
        for entry in entries:
            if "name" not in entry or "type" not in entry or "host" not in entry:
                logger.warning("name/type/host 누락, 건너뜀: %s", entry)
                continue
            dbs.append(DatabaseEntry(**{
                k: v for k, v in entry.items()
                if k in DatabaseEntry.__dataclass_fields__
            }))

        logger.info("로드된 DB: %d개", len(dbs))
        return cls(credentials=creds, databases=dbs)

    def get_by_type(self, db_type: str) -> list[DatabaseEntry]:
        return [db for db in self.databases if db.type == db_type]
