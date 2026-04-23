# db-perf-mcp-server

DB 성능 모니터링을 위한 MCP 서버입니다. FastMCP 기반 Python 서버로, PostgreSQL/MySQL/Valkey에 대한 성능 모니터링 도구를 제공합니다.

쿼리는 Google의 [MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox)의 db-performance-monitoring-mcp에서 가져왔습니다.

## 설계

- 도구는 DB 타입별로 공통 (pg_list_active_queries, mysql_execute_sql 등)
- 모든 도구에 `db_name` 파라미터가 있어 어떤 DB 인스턴스에 실행할지 선택
- DB 인스턴스 추가/제거는 Secrets Manager의 DATABASES JSON만 수정

## 도구 목록

| 타입 | 도구 수 | 주요 도구 |
|------|---------|-----------|
| 공통 | 1 | list_databases |
| PostgreSQL | 22 | pg_execute_sql, pg_list_active_queries, pg_list_locks 등 |
| MySQL | 5 | mysql_execute_sql, mysql_list_active_queries 등 |
| Valkey | 1 | valkey_execute_command |

## 시크릿 등록

```bash
aws secretsmanager create-secret \
  --name devops-dba-dbperf-prd \
  --secret-string '{
    "PG_USER": "dba_readonly",
    "PG_PASSWORD": "***",
    "MYSQL_USER": "dba_readonly",
    "MYSQL_PASSWORD": "***",
    "VALKEY_USERNAME": "default",
    "VALKEY_PASSWORD": "***",
    "DATABASES": "[{\"name\":\"service\",\"type\":\"postgres\",\"host\":\"service-pg.rds.amazonaws.com\"},{\"name\":\"ad\",\"type\":\"mysql\",\"host\":\"ad-mysql.rds.amazonaws.com\"},{\"name\":\"cache\",\"type\":\"valkey\",\"host\":\"cache.valkey.amazonaws.com\"}]"
  }'
```

### DATABASES JSON 형식

```json
[
  {"name": "service", "type": "postgres", "host": "service-pg.rds.amazonaws.com"},
  {"name": "ad", "type": "mysql", "host": "ad-mysql.rds.amazonaws.com"},
  {"name": "cache", "type": "valkey", "host": "cache.valkey.amazonaws.com"}
]
```

port, database, address, label은 모두 선택 필드이며 타입별 기본값이 적용됩니다.

## 배포

```bash
kubectl apply -f k8s/external-secret.yaml
kubectl apply -f k8s/deployment.yaml
```

## 클러스터 내 접근

```
http://db-perf-mcp-server.db.svc.cluster.local/mcp
```
    "DATABASES": "[{\"name\":\"service\",\"type\":\"postgres\",\"host\":\"service-pg.rds.amazonaws.com\"},{\"name\":\"ad\",\"type\":\"mysql\",\"host\":\"ad-mysql.rds.amazonaws.com\"},{\"name\":\"cache\",\"type\":\"valkey\",\"host\":\"cache.valkey.amazonaws.com\"}]"
  }'
```

### DATABASES JSON 형식

```json
[
  {"name": "service", "type": "postgres", "host": "service-pg.rds.amazonaws.com"},
  {"name": "ad", "type": "mysql", "host": "ad-mysql.rds.amazonaws.com"},
  {"name": "cache", "type": "valkey", "host": "cache.valkey.amazonaws.com"}
]
```

| 필드 | 필수 | 설명 |
|------|------|------|
| name | O | db_name 파라미터로 사용되는 식별자 |
| type | O | postgres, mysql, valkey |
| host | O | DB 호스트 |
| port | - | 기본값: postgres=5432, mysql=3306 |
| database | - | 기본값: postgres=postgres, mysql=information_schema |
| address | - | valkey 전용. 미지정 시 {host}:6379 |
| label | - | 로그에 사용할 표시명 |

## 배포

```bash
kubectl apply -f k8s/external-secret.yaml
kubectl apply -f k8s/deployment.yaml
```

## 클러스터 내 접근

```
http://db-perf-mcp-server.db.svc.cluster.local/mcp
```

## DB 서버 추가/제거

Secrets Manager의 DATABASES JSON만 수정 후 Pod 재시작하면 됩니다.
