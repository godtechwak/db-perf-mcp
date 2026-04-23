"""PostgreSQL MCP 도구."""

from __future__ import annotations

from tools import mcp
from tools.helpers import pg_query, log_tool_call
from queries import postgres as pg_q


# ── 서버 레벨 도구 (database 무관) ──
@mcp.tool()
@log_tool_call
async def pg_execute_sql(db_name: str, sql: str, database: str | None = None) -> str:
    """Execute arbitrary SQL on a PostgreSQL database (5s timeout). Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, sql, database=database, timeout=5)


@mcp.tool()
@log_tool_call
async def pg_database_overview(db_name: str) -> str:
    """Get a high-level overview of a PostgreSQL server: version, replica status, uptime, connections."""
    return await pg_query(db_name, pg_q.DATABASE_OVERVIEW)


@mcp.tool()
@log_tool_call
async def pg_list_active_queries(
    db_name: str,
    min_duration: str | None = None,
    exclude_application_names: str | None = None,
    limit: int = 50,
) -> str:
    """List currently running queries on a PostgreSQL database."""
    return await pg_query(db_name, pg_q.LIST_ACTIVE_QUERIES, [min_duration, exclude_application_names, limit])


@mcp.tool()
@log_tool_call
async def pg_list_locks(db_name: str) -> str:
    """List current locks held by active processes in PostgreSQL."""
    return await pg_query(db_name, pg_q.LIST_LOCKS)


@mcp.tool()
@log_tool_call
async def pg_replication_stats(db_name: str) -> str:
    """Show replication lag statistics for PostgreSQL replicas."""
    return await pg_query(db_name, pg_q.REPLICATION_STATS)


@mcp.tool()
@log_tool_call
async def pg_list_database_stats(
    db_name: str,
    database_name: str | None = None,
    include_templates: bool = False,
    database_owner: str | None = None,
    default_tablespace: str | None = None,
    order_by: str | None = None,
    limit: int = 10,
) -> str:
    """Show database-level performance statistics for PostgreSQL."""
    return await pg_query(db_name, pg_q.LIST_DATABASE_STATS,
        [database_name, include_templates, database_owner, default_tablespace, order_by, limit])


@mcp.tool()
@log_tool_call
async def pg_list_logical_databases(db_name: str) -> str:
    """List all logical databases in a PostgreSQL server with owner, encoding, size. Use the returned database names as the 'database' parameter in other tools."""
    return await pg_query(db_name, pg_q.LIST_LOGICAL_DATABASES)


@mcp.tool()
@log_tool_call
async def pg_list_roles(db_name: str, role_name: str | None = None, limit: int = 50) -> str:
    """List user-created roles in a PostgreSQL instance."""
    return await pg_query(db_name, pg_q.LIST_ROLES, [role_name, limit])


@mcp.tool()
@log_tool_call
async def pg_list_tablespaces(db_name: str, tablespace_name: str | None = None, limit: int = 50) -> str:
    """List tablespaces in a PostgreSQL database."""
    return await pg_query(db_name, pg_q.LIST_TABLESPACES, [tablespace_name, limit])


@mcp.tool()
@log_tool_call
async def pg_list_pg_settings(db_name: str, setting_name: str | None = None, limit: int = 50) -> str:
    """List PostgreSQL configuration settings."""
    return await pg_query(db_name, pg_q.LIST_PG_SETTINGS, [setting_name, limit])


@mcp.tool()
@log_tool_call
async def pg_long_running_transactions(db_name: str, min_duration: str = "5 minutes", limit: int = 20) -> str:
    """List long-running transactions in PostgreSQL."""
    return await pg_query(db_name, pg_q.LONG_RUNNING_TRANSACTIONS, [min_duration, limit])


# ── database 레벨 도구 (database 파라미터 지원) ──

@mcp.tool()
@log_tool_call
async def pg_list_schemas(
    db_name: str, database: str | None = None,
    schema_name: str | None = None, owner: str | None = None, limit: int = 10,
) -> str:
    """List schemas in a PostgreSQL database. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_SCHEMAS, [schema_name, owner, limit], database=database)


@mcp.tool()
@log_tool_call
async def pg_list_table_stats(
    db_name: str, database: str | None = None,
    schema_name: str = "public", table_name: str | None = None,
    owner: str | None = None, sort_by: str | None = None, limit: int = 50,
) -> str:
    """Show table-level statistics for PostgreSQL. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_TABLE_STATS,
        [schema_name, table_name, owner, sort_by, limit], database=database)


@mcp.tool()
@log_tool_call
async def pg_list_table_columns(
    db_name: str, database: str | None = None,
    schema_name: str | None = None, table_name: str | None = None, limit: int = 100,
) -> str:
    """List table columns (schema) for PostgreSQL. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_TABLE_COLUMNS, [schema_name, table_name, limit], database=database)


@mcp.tool()
@log_tool_call
async def pg_list_indexes(
    db_name: str, database: str | None = None,
    schema_name: str | None = None, table_name: str | None = None,
    index_name: str | None = None, only_unused: bool = False, limit: int = 50,
) -> str:
    """List indexes in a PostgreSQL database. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_INDEXES,
        [schema_name, table_name, index_name, only_unused, limit], database=database)


@mcp.tool()
@log_tool_call
async def pg_list_sequences(
    db_name: str, database: str | None = None,
    schema_name: str | None = None, sequence_name: str | None = None, limit: int = 50,
) -> str:
    """List sequences in a PostgreSQL database. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_SEQUENCES, [schema_name, sequence_name, limit], database=database)


@mcp.tool()
@log_tool_call
async def pg_list_views(
    db_name: str, database: str | None = None,
    view_name: str | None = None, schema_name: str | None = None, limit: int = 50,
) -> str:
    """List views in a PostgreSQL database. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_VIEWS, [view_name, schema_name, limit], database=database)


@mcp.tool()
@log_tool_call
async def pg_list_triggers(
    db_name: str, database: str | None = None,
    trigger_name: str | None = None, schema_name: str | None = None,
    table_name: str | None = None, limit: int = 50,
) -> str:
    """List triggers in a PostgreSQL database. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_TRIGGERS, [trigger_name, schema_name, table_name, limit], database=database)


@mcp.tool()
@log_tool_call
async def pg_list_installed_extensions(db_name: str, database: str | None = None) -> str:
    """List installed extensions in a PostgreSQL database. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_INSTALLED_EXTENSIONS, database=database)


@mcp.tool()
@log_tool_call
async def pg_list_available_extensions(db_name: str, database: str | None = None) -> str:
    """List available extensions in a PostgreSQL database. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_AVAILABLE_EXTENSIONS, database=database)


@mcp.tool()
@log_tool_call
async def pg_list_query_stats(
    db_name: str, database: str | None = None,
    database_name: str | None = None, limit: int = 50,
) -> str:
    """Show query statistics from pg_stat_statements. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_QUERY_STATS, [database_name, limit], database=database)


@mcp.tool()
@log_tool_call
async def pg_list_publication_tables(
    db_name: str, database: str | None = None,
    table_names: str | None = None, publication_names: str | None = None,
    schema_names: str | None = None, limit: int = 50,
) -> str:
    """List publication tables for logical replication. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_PUBLICATION_TABLES,
        [table_names, publication_names, schema_names, limit], database=database)


@mcp.tool()
@log_tool_call
async def pg_get_column_cardinality(
    db_name: str, table_name: str, database: str | None = None,
    schema_name: str = "public", column_name: str | None = None,
) -> str:
    """Estimate column cardinality using PostgreSQL internal statistics. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.GET_COLUMN_CARDINALITY, [schema_name, table_name, column_name], database=database)


@mcp.tool()
@log_tool_call
async def pg_list_stored_procedures(
    db_name: str, database: str | None = None,
    role_name: str | None = None, schema_name: str | None = None, limit: int = 20,
) -> str:
    """List stored procedures in a PostgreSQL database. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_STORED_PROCEDURES, [role_name, schema_name, limit], database=database)


@mcp.tool()
@log_tool_call
async def pg_list_tables(
    db_name: str, database: str | None = None,
    schema_name: str | None = None, limit: int = 200,
) -> str:
    """List tables in a PostgreSQL database with owner, estimated rows, and size. Specify 'database' to connect to a specific logical database."""
    return await pg_query(db_name, pg_q.LIST_TABLES, [schema_name, limit], database=database)


@mcp.tool()
@log_tool_call
async def pg_get_query_plan(db_name: str, sql_statement: str, database: str) -> str:
    """Get EXPLAIN output for a PostgreSQL query in JSON format.
    Use pg_list_logical_databases to find the correct database name."""
    return await pg_query(
        db_name,
        f"EXPLAIN (BUFFERS, FORMAT JSON) {sql_statement}",
        database=database,
        timeout=10,
    )
