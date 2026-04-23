"""MySQL MCP 도구."""

from __future__ import annotations

from tools import mcp
from tools.helpers import mysql_query, log_tool_call
from queries import mysql as my_q

@mcp.tool()
@log_tool_call
async def mysql_execute_sql(db_name: str, sql: str) -> str:
    """Execute arbitrary SQL on a MySQL database (5s timeout)."""
    return await mysql_query(db_name, sql, timeout=5)


@mcp.tool()
@log_tool_call
async def mysql_list_active_queries(db_name: str, min_duration_secs: int = 0, limit: int = 100) -> str:
    """List currently running queries on a MySQL database."""
    return await mysql_query(db_name, my_q.LIST_ACTIVE_QUERIES,
        (min_duration_secs, min_duration_secs, limit))


@mcp.tool()
@log_tool_call
async def mysql_list_table_fragmentation(
    db_name: str, table_schema: str = "", table_name: str = "",
    data_free_threshold_bytes: int = 1, limit: int = 10,
) -> str:
    """List table fragmentation in a MySQL database."""
    return await mysql_query(db_name, my_q.LIST_TABLE_FRAGMENTATION,
        (table_schema, table_schema, table_name, table_name, data_free_threshold_bytes, limit))


@mcp.tool()
@log_tool_call
async def mysql_list_tables_missing_unique_indexes(db_name: str, table_schema: str = "", limit: int = 50) -> str:
    """List tables missing unique indexes in a MySQL database."""
    return await mysql_query(db_name, my_q.LIST_TABLES_MISSING_UNIQUE_INDEXES,
        (table_schema, table_schema, limit))


@mcp.tool()
@log_tool_call
async def mysql_list_table_stats(
    db_name: str, table_schema: str = "", table_name: str = "", limit: int = 50,
) -> str:
    """Show table-level statistics for MySQL: row count, data size, index size, engine, collation."""
    return await mysql_query(db_name, my_q.LIST_TABLE_STATS,
        (table_schema, table_schema, table_name, table_name, limit))


@mcp.tool()
@log_tool_call
async def mysql_get_query_plan(db_name: str, sql_statement: str) -> str:
    """Get EXPLAIN output for a MySQL query in JSON format."""
    return await mysql_query(db_name, f"EXPLAIN FORMAT=JSON {sql_statement}")


@mcp.tool()
@log_tool_call
async def mysql_list_table_columns(
    db_name: str, table_schema: str = "", table_name: str = "", limit: int = 200,
) -> str:
    """List table columns (schema) for MySQL: column name, type, nullable, key, default, comment."""
    return await mysql_query(db_name, my_q.LIST_TABLE_COLUMNS,
        (table_schema, table_schema, table_name, table_name, limit))


@mcp.tool()
@log_tool_call
async def mysql_list_index_stats(
    db_name: str, table_schema: str = "", table_name: str = "", limit: int = 50,
) -> str:
    """List index usage statistics for MySQL. Shows which indexes are used or unused."""
    return await mysql_query(db_name, my_q.LIST_INDEX_STATS,
        (table_schema, table_schema, table_name, table_name, limit))


@mcp.tool()
@log_tool_call
async def mysql_list_locks(db_name: str, limit: int = 50) -> str:
    """List current lock waits in MySQL: waiting and blocking transactions."""
    return await mysql_query(db_name, my_q.LIST_LOCKS, (limit,))


@mcp.tool()
@log_tool_call
async def mysql_list_connections(db_name: str, limit: int = 50) -> str:
    """List connection summary grouped by user, host, db, and command."""
    return await mysql_query(db_name, my_q.LIST_CONNECTIONS, (limit,))


@mcp.tool()
@log_tool_call
async def mysql_list_global_variables(db_name: str, variable_name: str | None = None, limit: int = 50) -> str:
    """List MySQL global variables. Filter by variable_name keyword."""
    return await mysql_query(db_name, my_q.LIST_GLOBAL_VARIABLES,
        (variable_name, variable_name, limit))
