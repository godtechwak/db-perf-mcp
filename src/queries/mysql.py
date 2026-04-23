"""MySQL 쿼리 정의. genai-toolbox db-performance-monitoring-mcp에서 추출."""

LIST_ACTIVE_QUERIES = """
SELECT
    p.id AS processlist_id,
    substring(IFNULL(p.info, t.trx_query), 1, 100) AS query,
    t.trx_started AS trx_started,
    (UNIX_TIMESTAMP(UTC_TIMESTAMP()) - UNIX_TIMESTAMP(t.trx_started)) AS trx_duration_seconds,
    (UNIX_TIMESTAMP(UTC_TIMESTAMP()) - UNIX_TIMESTAMP(t.trx_wait_started)) AS trx_wait_duration_seconds,
    p.time AS query_time, t.trx_state AS trx_state, p.state AS process_state,
    IF(p.host IS NULL OR p.host = '', p.user, concat(p.user, '@', SUBSTRING_INDEX(p.host, ':', 1))) AS user,
    t.trx_rows_locked AS trx_rows_locked, t.trx_rows_modified AS trx_rows_modified, p.db AS db
FROM information_schema.processlist p
LEFT OUTER JOIN information_schema.innodb_trx t ON p.id = t.trx_mysql_thread_id
WHERE (%s IS NULL OR p.time >= %s)
    AND p.id != CONNECTION_ID()
    AND Command NOT IN ('Binlog Dump', 'Binlog Dump GTID', 'Connect', 'Connect Out', 'Register Slave')
    AND User NOT IN ('system user', 'event_scheduler')
    AND (t.trx_id is NOT NULL OR command != 'Sleep')
ORDER BY t.trx_started LIMIT %s;
"""

LIST_TABLE_FRAGMENTATION = """
SELECT table_schema, table_name, data_length AS data_size, index_length AS index_size,
    data_free, ROUND((data_free / (data_length + index_length)) * 100, 2) AS fragmentation_percentage
FROM information_schema.tables
WHERE table_schema NOT IN ('sys', 'performance_schema', 'mysql', 'information_schema')
    AND (COALESCE(%s, '') = '' OR table_schema = %s)
    AND (COALESCE(%s, '') = '' OR table_name = %s)
    AND data_free >= %s
ORDER BY fragmentation_percentage DESC, table_schema, table_name LIMIT %s;
"""

LIST_TABLES_MISSING_UNIQUE_INDEXES = """
SELECT tab.table_schema, tab.table_name
FROM information_schema.tables tab
LEFT JOIN information_schema.table_constraints tco
    ON tab.table_schema = tco.table_schema AND tab.table_name = tco.table_name
    AND tco.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
WHERE tco.constraint_type IS NULL
    AND tab.table_schema NOT IN('mysql', 'information_schema', 'performance_schema', 'sys')
    AND tab.table_type = 'BASE TABLE'
    AND (COALESCE(%s, '') = '' OR tab.table_schema = %s)
ORDER BY tab.table_schema, tab.table_name LIMIT %s;
"""

LIST_TABLE_STATS = """
SELECT
    t.table_schema,
    t.table_name,
    t.engine,
    t.table_rows,
    t.avg_row_length,
    t.data_length   AS data_size,
    t.index_length  AS index_size,
    t.data_free,
    t.auto_increment,
    t.create_time,
    t.update_time,
    t.table_collation
FROM information_schema.tables t
WHERE t.table_type = 'BASE TABLE'
    AND t.table_schema NOT IN ('sys', 'performance_schema', 'mysql', 'information_schema')
    AND (COALESCE(%s, '') = '' OR t.table_schema = %s)
    AND (COALESCE(%s, '') = '' OR t.table_name = %s)
ORDER BY t.data_length DESC LIMIT %s;
"""

LIST_TABLE_COLUMNS = """
SELECT
    c.table_schema,
    c.table_name,
    c.column_name,
    c.ordinal_position,
    c.column_default,
    c.is_nullable,
    c.data_type,
    c.character_maximum_length,
    c.numeric_precision,
    c.numeric_scale,
    c.column_type,
    c.column_key,
    c.extra,
    c.column_comment
FROM information_schema.columns c
WHERE c.table_schema NOT IN ('sys', 'performance_schema', 'mysql', 'information_schema')
    AND (COALESCE(%s, '') = '' OR c.table_schema = %s)
    AND (COALESCE(%s, '') = '' OR c.table_name = %s)
ORDER BY c.table_schema, c.table_name, c.ordinal_position
LIMIT %s;
"""

LIST_INDEX_STATS = """
SELECT
    s.table_schema,
    s.table_name,
    s.index_name,
    s.non_unique,
    GROUP_CONCAT(s.column_name ORDER BY s.seq_in_index) AS columns,
    s.index_type,
    t.rows_read,
    CASE WHEN t.rows_read IS NULL OR t.rows_read = 0 THEN 'UNUSED' ELSE 'USED' END AS usage_status
FROM information_schema.statistics s
LEFT JOIN sys.schema_index_statistics t
    ON s.table_schema = t.table_schema
    AND s.table_name = t.table_name
    AND s.index_name = t.index_name
WHERE s.table_schema NOT IN ('sys', 'performance_schema', 'mysql', 'information_schema')
    AND (COALESCE(%s, '') = '' OR s.table_schema = %s)
    AND (COALESCE(%s, '') = '' OR s.table_name = %s)
GROUP BY s.table_schema, s.table_name, s.index_name, s.non_unique, s.index_type, t.rows_read
ORDER BY t.rows_read ASC, s.table_schema, s.table_name, s.index_name
LIMIT %s;
"""

LIST_LOCKS = """
SELECT
    r.trx_id AS waiting_trx_id,
    r.trx_mysql_thread_id AS waiting_thread,
    r.trx_query AS waiting_query,
    b.trx_id AS blocking_trx_id,
    b.trx_mysql_thread_id AS blocking_thread,
    b.trx_query AS blocking_query,
    b.trx_started AS blocking_trx_started,
    (UNIX_TIMESTAMP(NOW()) - UNIX_TIMESTAMP(b.trx_started)) AS blocking_duration_seconds
FROM performance_schema.data_lock_waits w
JOIN information_schema.innodb_trx r ON r.trx_id = w.REQUESTING_ENGINE_TRANSACTION_ID
JOIN information_schema.innodb_trx b ON b.trx_id = w.BLOCKING_ENGINE_TRANSACTION_ID
ORDER BY blocking_duration_seconds DESC
LIMIT %s;
"""

LIST_CONNECTIONS = """
SELECT
    user,
    SUBSTRING_INDEX(host, ':', 1) AS client_host,
    db,
    command,
    COUNT(*) AS connection_count,
    SUM(CASE WHEN command != 'Sleep' THEN 1 ELSE 0 END) AS active_count,
    SUM(CASE WHEN command = 'Sleep' THEN 1 ELSE 0 END) AS idle_count
FROM information_schema.processlist
WHERE user NOT IN ('system user', 'event_scheduler', 'rdsadmin')
GROUP BY user, SUBSTRING_INDEX(host, ':', 1), db, command
ORDER BY connection_count DESC
LIMIT %s;
"""

LIST_GLOBAL_VARIABLES = """
SELECT
    variable_name,
    variable_value
FROM performance_schema.global_variables
WHERE (%s IS NULL OR variable_name LIKE CONCAT('%%', %s, '%%'))
ORDER BY variable_name
LIMIT %s;
"""
