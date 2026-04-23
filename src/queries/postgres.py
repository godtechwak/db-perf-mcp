"""PostgreSQL 쿼리 정의. genai-toolbox db-performance-monitoring-mcp에서 추출."""

DATABASE_OVERVIEW = """
SELECT
    current_setting('server_version') AS pg_version,
    pg_is_in_recovery() AS is_replica,
    (now() - pg_postmaster_start_time())::TEXT AS uptime,
    current_setting('max_connections')::int AS max_connections,
    (SELECT count(*) FROM pg_stat_activity) AS current_connections,
    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') AS active_connections,
    round(
        (100.0 * (SELECT count(*) FROM pg_stat_activity) / current_setting('max_connections')::int),
        2
    ) AS pct_connections_used;
"""

LIST_ACTIVE_QUERIES = """
SELECT
    pid, usename AS user, datname, application_name, client_addr, state,
    wait_event_type, wait_event, backend_start, xact_start, query_start,
    now() - query_start AS query_duration, query
FROM pg_stat_activity
WHERE state = 'active'
    AND ($1::INTERVAL IS NULL OR now() - query_start >= $1::INTERVAL)
    AND ($2::text IS NULL OR application_name NOT IN (
        SELECT trim(app) FROM unnest(string_to_array($2, ',')) AS app))
ORDER BY query_duration DESC
LIMIT COALESCE($3::int, 50);
"""

LIST_LOCKS = """
SELECT locked.pid, locked.usename, locked.query,
    string_agg(locked.transactionid::text,':') as trxid,
    string_agg(locked.lockinfo,'||') as locks
FROM (
    SELECT a.pid, a.usename, a.query, l.transactionid,
        (l.granted::text||','||coalesce(l.relation::regclass,0)::text||','||l.mode::text)::text as lockinfo
    FROM pg_stat_activity a
    JOIN pg_locks l ON l.pid = a.pid AND a.pid != pg_backend_pid()
) as locked
GROUP BY locked.pid, locked.usename, locked.query;
"""

REPLICATION_STATS = """
SELECT pid, usename, application_name, backend_xmin, client_addr, state, sync_state,
    pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), sent_lsn)) AS sent_lag,
    pg_size_pretty(pg_wal_lsn_diff(sent_lsn, write_lsn)) AS write_lag,
    pg_size_pretty(pg_wal_lsn_diff(write_lsn, flush_lsn)) AS flush_lag,
    pg_size_pretty(pg_wal_lsn_diff(flush_lsn, replay_lsn)) AS replay_lag,
    pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)) AS total_lag
FROM pg_stat_replication;
"""

LIST_INSTALLED_EXTENSIONS = """
SELECT e.extname AS name, e.extversion AS version, n.nspname AS schema,
    pg_get_userbyid(e.extowner) AS owner, c.description
FROM pg_catalog.pg_extension e
LEFT JOIN pg_catalog.pg_namespace n ON n.oid = e.extnamespace
LEFT JOIN pg_catalog.pg_description c ON c.objoid = e.oid
    AND c.classoid = 'pg_catalog.pg_extension'::pg_catalog.regclass
ORDER BY 1;
"""

LIST_AVAILABLE_EXTENSIONS = """
SELECT name, default_version, comment as description
FROM pg_available_extensions ORDER BY name;
"""

LIST_DATABASE_STATS = """
WITH database_stats AS (
    SELECT s.datname AS database_name, d.datallowconn AS is_connectable,
        pg_get_userbyid(d.datdba) AS database_owner, ts.spcname AS default_tablespace,
        CASE WHEN (s.blks_hit + s.blks_read) = 0 THEN 0
            ELSE round((s.blks_hit * 100.0) / (s.blks_hit + s.blks_read), 2)
        END AS cache_hit_ratio_percent,
        s.blks_read AS blocks_read_from_disk, s.blks_hit AS blocks_hit_in_cache,
        s.xact_commit, s.xact_rollback,
        round(s.xact_rollback * 100.0 / (s.xact_commit + s.xact_rollback + 1), 2) AS rollback_ratio_percent,
        s.tup_returned AS rows_returned_by_queries, s.tup_fetched AS rows_fetched_by_scans,
        s.tup_inserted, s.tup_updated, s.tup_deleted,
        s.temp_files, s.temp_bytes AS temp_size_bytes,
        s.conflicts, s.deadlocks,
        s.numbackends AS active_connections, s.stats_reset AS statistics_last_reset,
        pg_database_size(s.datid) AS database_size_bytes
    FROM pg_stat_database s
    JOIN pg_database d ON d.oid = s.datid
    JOIN pg_tablespace ts ON ts.oid = d.dattablespace
    WHERE s.datname NOT IN ('cloudsqladmin')
        AND ($2::boolean IS TRUE OR d.datistemplate IS FALSE)
)
SELECT * FROM database_stats
WHERE ($1::text IS NULL OR database_name LIKE '%' || $1::text || '%')
    AND ($3::text IS NULL OR database_owner LIKE '%' || $3::text || '%')
    AND ($4::text IS NULL OR default_tablespace LIKE '%' || $4::text || '%')
ORDER BY
    CASE WHEN $5::text = 'size' THEN database_size_bytes END DESC,
    CASE WHEN $5::text = 'commit' THEN xact_commit END DESC,
    database_name
LIMIT COALESCE($6::int, 10);
"""

LIST_TABLE_STATS = """
WITH table_stats AS (
    SELECT s.schemaname AS schema_name, s.relname AS table_name,
        pg_catalog.pg_get_userbyid(c.relowner) AS owner,
        pg_total_relation_size(s.relid) AS total_size_bytes,
        s.seq_scan, s.idx_scan,
        CASE WHEN (s.seq_scan + s.idx_scan) = 0 THEN 0
            ELSE round((s.idx_scan * 100.0) / (s.seq_scan + s.idx_scan), 2)
        END AS idx_scan_ratio_percent,
        s.n_live_tup AS live_rows, s.n_dead_tup AS dead_rows,
        CASE WHEN (s.n_live_tup + s.n_dead_tup) = 0 THEN 0
            ELSE round((s.n_dead_tup * 100.0) / (s.n_live_tup + s.n_dead_tup), 2)
        END AS dead_row_ratio_percent,
        s.n_tup_ins, s.n_tup_upd, s.n_tup_del,
        s.last_vacuum, s.last_autovacuum, s.last_autoanalyze
    FROM pg_stat_all_tables s
    JOIN pg_catalog.pg_class c ON s.relid = c.oid
)
SELECT * FROM table_stats
WHERE ($1::text IS NULL OR schema_name LIKE '%' || $1::text || '%')
    AND ($2::text IS NULL OR table_name LIKE '%' || $2::text || '%')
    AND ($3::text IS NULL OR owner LIKE '%' || $3::text || '%')
ORDER BY
    CASE WHEN $4::text = 'size' THEN total_size_bytes
         WHEN $4::text = 'dead_rows' THEN dead_rows
         WHEN $4::text = 'seq_scan' THEN seq_scan
         WHEN $4::text = 'idx_scan' THEN idx_scan
         ELSE seq_scan END DESC
LIMIT COALESCE($5::int, 50);
"""

LIST_QUERY_STATS = """
SELECT d.datname, s.query, s.calls, s.total_exec_time, s.min_exec_time,
    s.max_exec_time, s.mean_exec_time, s.rows, s.shared_blks_hit, s.shared_blks_read
FROM pg_stat_statements s
JOIN pg_database d ON d.oid = s.dbid
WHERE d.datname <> 'cloudsqladmin'
    AND ($1::text IS NULL OR d.datname LIKE '%' || $1::text || '%')
ORDER BY total_exec_time DESC
LIMIT COALESCE($2::int, 50);
"""

LIST_INDEXES = """
WITH IndexDetails AS (
    SELECT s.schemaname AS schema_name, t.relname AS table_name, i.relname AS index_name,
        am.amname AS index_type, ix.indisunique AS is_unique, ix.indisprimary AS is_primary,
        pg_get_indexdef(i.oid) AS index_definition, pg_relation_size(i.oid) AS index_size_bytes,
        s.idx_scan AS index_scans, s.idx_tup_read AS tuples_read, s.idx_tup_fetch AS tuples_fetched,
        CASE WHEN s.idx_scan > 0 THEN true ELSE false END AS is_used
    FROM pg_catalog.pg_class t
    JOIN pg_catalog.pg_index ix ON t.oid = ix.indrelid
    JOIN pg_catalog.pg_class i ON i.oid = ix.indexrelid
    JOIN pg_catalog.pg_am am ON i.relam = am.oid
    JOIN pg_catalog.pg_stat_all_indexes s ON i.oid = s.indexrelid
    WHERE t.relkind = 'r'
        AND s.schemaname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        AND s.schemaname NOT LIKE 'pg_temp_%'
)
SELECT * FROM IndexDetails
WHERE ($1::text IS NULL OR schema_name LIKE '%' || $1 || '%')
    AND ($2::text IS NULL OR table_name LIKE '%' || $2 || '%')
    AND ($3::text IS NULL OR index_name LIKE '%' || $3 || '%')
    AND ($4::boolean IS NOT TRUE OR is_used IS FALSE)
ORDER BY schema_name, table_name, index_name
LIMIT COALESCE($5::int, 50);
"""

LIST_SCHEMAS = """
WITH schema_grants AS (
    SELECT schema_oid, jsonb_object_agg(grantee, privileges) AS grants FROM (
        SELECT n.oid AS schema_oid,
            CASE WHEN p.grantee = 0 THEN 'PUBLIC' ELSE pg_catalog.pg_get_userbyid(p.grantee) END AS grantee,
            jsonb_agg(p.privilege_type ORDER BY p.privilege_type) AS privileges
        FROM pg_catalog.pg_namespace n, aclexplode(n.nspacl) p
        WHERE n.nspacl IS NOT NULL GROUP BY n.oid, grantee
    ) permissions_by_grantee GROUP BY schema_oid
),
all_schemas AS (
    SELECT n.nspname AS schema_name, pg_catalog.pg_get_userbyid(n.nspowner) AS owner,
        COALESCE(sg.grants, '{}'::jsonb) AS grants,
        (SELECT COUNT(*) FROM pg_catalog.pg_class c WHERE c.relnamespace = n.oid AND c.relkind = 'r') AS tables,
        (SELECT COUNT(*) FROM pg_catalog.pg_class c WHERE c.relnamespace = n.oid AND c.relkind = 'v') AS views,
        (SELECT COUNT(*) FROM pg_catalog.pg_proc p WHERE p.pronamespace = n.oid) AS functions
    FROM pg_catalog.pg_namespace n
    LEFT JOIN schema_grants sg ON n.oid = sg.schema_oid
)
SELECT * FROM all_schemas
WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
    AND schema_name NOT LIKE 'pg_temp_%' AND schema_name NOT LIKE 'pg_toast_temp_%'
    AND ($1::text IS NULL OR schema_name ILIKE '%' || $1::text || '%')
    AND ($2::text IS NULL OR owner ILIKE '%' || $2::text || '%')
ORDER BY schema_name LIMIT COALESCE($3::int, NULL);
"""

LIST_ROLES = """
WITH RoleDetails AS (
    SELECT r.rolname AS role_name, r.oid, r.rolconnlimit AS connection_limit,
        r.rolsuper AS is_superuser, r.rolinherit AS inherits_privileges,
        r.rolcreaterole AS can_create_roles, r.rolcreatedb AS can_create_db,
        r.rolcanlogin AS can_login, r.rolreplication AS is_replication_role,
        r.rolbypassrls AS bypass_rls, r.rolvaliduntil AS valid_until,
        ARRAY(SELECT m_r.rolname FROM pg_auth_members pam JOIN pg_roles m_r ON pam.member = m_r.oid WHERE pam.roleid = r.oid) AS direct_members,
        ARRAY(SELECT g_r.rolname FROM pg_auth_members pam JOIN pg_roles g_r ON pam.roleid = g_r.oid WHERE pam.member = r.oid) AS member_of
    FROM pg_roles r
    WHERE r.rolname NOT LIKE 'cloudsql%' AND r.rolname NOT LIKE 'alloydb_%' AND r.rolname NOT LIKE 'pg_%'
)
SELECT * FROM RoleDetails
WHERE ($1::text IS NULL OR role_name LIKE '%' || $1 || '%')
ORDER BY role_name LIMIT COALESCE($2::int, 50);
"""

LIST_SEQUENCES = """
SELECT sequencename as sequence_name, schemaname as schema_name, sequenceowner as sequence_owner,
    data_type, start_value, min_value, max_value, increment_by, last_value
FROM pg_sequences
WHERE ($1::text IS NULL OR schemaname LIKE '%' || $1 || '%')
    AND ($2::text IS NULL OR sequencename LIKE '%' || $2 || '%')
ORDER BY schema_name, sequence_name LIMIT COALESCE($3::int, 50);
"""

LIST_VIEWS = """
WITH list_views AS (
    SELECT schemaname AS schema_name, viewname AS view_name, viewowner AS owner_name, definition
    FROM pg_views
)
SELECT * FROM list_views
WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
    AND schema_name NOT LIKE 'pg_temp_%'
    AND ($1::text IS NULL OR view_name ILIKE '%' || $1::text || '%')
    AND ($2::text IS NULL OR schema_name ILIKE '%' || $2::text || '%')
ORDER BY schema_name, view_name LIMIT COALESCE($3::int, 50);
"""

LIST_TRIGGERS = """
WITH trigger_list AS (
    SELECT t.tgname AS trigger_name, n.nspname AS schema_name, c.relname AS table_name,
        CASE t.tgenabled WHEN 'O' THEN 'ENABLED' WHEN 'D' THEN 'DISABLED' WHEN 'R' THEN 'REPLICA' WHEN 'A' THEN 'ALWAYS' END AS status,
        CASE WHEN (t.tgtype::int & 2) = 2 THEN 'BEFORE' WHEN (t.tgtype::int & 64) = 64 THEN 'INSTEAD OF' ELSE 'AFTER' END AS timing,
        concat_ws(', ',
            CASE WHEN (t.tgtype::int & 4) = 4 THEN 'INSERT' END,
            CASE WHEN (t.tgtype::int & 16) = 16 THEN 'UPDATE' END,
            CASE WHEN (t.tgtype::int & 8) = 8 THEN 'DELETE' END,
            CASE WHEN (t.tgtype::int & 32) = 32 THEN 'TRUNCATE' END) AS events,
        CASE WHEN (t.tgtype::int & 1) = 1 THEN 'ROW' ELSE 'STATEMENT' END AS activation_level,
        p.proname AS function_name, pg_get_triggerdef(t.oid) AS definition
    FROM pg_trigger t
    JOIN pg_class c ON t.tgrelid = c.oid
    JOIN pg_namespace n ON c.relnamespace = n.oid
    LEFT JOIN pg_proc p ON t.tgfoid = p.oid
    WHERE NOT t.tgisinternal
)
SELECT * FROM trigger_list
WHERE ($1::text IS NULL OR trigger_name LIKE '%' || $1::text || '%')
    AND ($2::text IS NULL OR schema_name LIKE '%' || $2::text || '%')
    AND ($3::text IS NULL OR table_name LIKE '%' || $3::text || '%')
ORDER BY schema_name, table_name, trigger_name LIMIT COALESCE($4::int, 50);
"""

LIST_TABLESPACES = """
WITH tablespace_info AS (
    SELECT spcname AS tablespace_name, pg_catalog.pg_get_userbyid(spcowner) AS owner_name,
        CASE WHEN pg_catalog.has_tablespace_privilege(oid, 'CREATE') THEN pg_tablespace_size(oid) ELSE NULL END AS size_in_bytes,
        oid, spcacl, spcoptions
    FROM pg_tablespace
)
SELECT * FROM tablespace_info
WHERE ($1::text IS NULL OR tablespace_name LIKE '%' || $1::text || '%')
ORDER BY tablespace_name LIMIT COALESCE($2::int, 50);
"""

LIST_PG_SETTINGS = """
SELECT name, setting AS current_value, unit, short_desc, source,
    CASE context WHEN 'postmaster' THEN 'Yes' WHEN 'sighup' THEN 'No (Reload sufficient)' ELSE 'No' END AS requires_restart
FROM pg_settings
WHERE ($1::text IS NULL OR name LIKE '%' || $1::text || '%')
ORDER BY name LIMIT COALESCE($2::int, 50);
"""

LIST_PUBLICATION_TABLES = """
WITH publication_details AS (
    SELECT pt.pubname AS publication_name, pt.schemaname AS schema_name, pt.tablename AS table_name,
        p.puballtables AS publishes_all_tables, p.pubinsert AS publishes_inserts,
        p.pubupdate AS publishes_updates, p.pubdelete AS publishes_deletes,
        p.pubtruncate AS publishes_truncates,
        pg_catalog.pg_get_userbyid(p.pubowner) AS publication_owner
    FROM pg_catalog.pg_publication_tables pt
    JOIN pg_catalog.pg_publication p ON pt.pubname = p.pubname
)
SELECT * FROM publication_details
WHERE (NULLIF(TRIM($1::text), '') IS NULL OR table_name = ANY(regexp_split_to_array(TRIM($1::text), '\\s*,\\s*')))
    AND (NULLIF(TRIM($2::text), '') IS NULL OR publication_name = ANY(regexp_split_to_array(TRIM($2::text), '\\s*,\\s*')))
    AND (NULLIF(TRIM($3::text), '') IS NULL OR schema_name = ANY(regexp_split_to_array(TRIM($3::text), '\\s*,\\s*')))
ORDER BY publication_name, schema_name, table_name LIMIT COALESCE($4::int, 50);
"""

LONG_RUNNING_TRANSACTIONS = """
SELECT pid, datname, usename, application_name as appname, client_addr, state,
    now() - backend_start as conn_age, now() - xact_start as xact_age,
    now() - query_start as query_age, now() - state_change as last_activity_age,
    wait_event_type, wait_event, query
FROM pg_stat_activity
WHERE state <> 'idle'
    AND (now() - xact_start) > COALESCE($1::INTERVAL, interval '5 minutes')
    AND xact_start IS NOT NULL AND pid <> pg_backend_pid()
ORDER BY xact_age DESC LIMIT COALESCE($2::int, 20);
"""

GET_COLUMN_CARDINALITY = """
SELECT s.attname AS column_name,
    ROUND(CASE WHEN s.n_distinct < 0 THEN ABS(s.n_distinct) * c.reltuples ELSE s.n_distinct END) AS estimated_cardinality
FROM pg_stats s
JOIN pg_class c ON s.tablename = c.relname
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE s.schemaname = $1 AND s.tablename = $2 AND n.nspname = $1
    AND s.attname = COALESCE($3, s.attname)
ORDER BY estimated_cardinality DESC;
"""

LIST_STORED_PROCEDURES = """
SELECT n.nspname AS schema_name, p.proname AS name, r.rolname AS owner,
    l.lanname AS language, pg_catalog.pg_get_functiondef(p.oid) AS definition,
    pg_catalog.obj_description(p.oid, 'pg_proc') AS description
FROM pg_catalog.pg_proc p
JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
JOIN pg_catalog.pg_roles r ON r.oid = p.proowner
JOIN pg_catalog.pg_language l ON l.oid = p.prolang
WHERE p.prokind = 'p'
    AND ($1::text IS NULL OR r.rolname LIKE '%' || $1::text || '%')
    AND ($2::text IS NULL OR n.nspname LIKE '%' || $2::text || '%')
ORDER BY n.nspname, p.proname LIMIT COALESCE($3::int, 20);
"""

LIST_TABLE_COLUMNS = """
SELECT
    n.nspname AS schema_name,
    c.relname AS table_name,
    a.attname AS column_name,
    a.attnum AS ordinal_position,
    pg_get_expr(d.adbin, d.adrelid) AS column_default,
    CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END AS is_nullable,
    format_type(a.atttypid, a.atttypmod) AS data_type,
    CASE WHEN pk.contype = 'p' THEN 'PRI'
         WHEN uk.contype = 'u' THEN 'UNI'
         ELSE '' END AS column_key,
    col_description(c.oid, a.attnum) AS column_comment
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
LEFT JOIN pg_constraint pk ON pk.conrelid = c.oid AND a.attnum = ANY(pk.conkey) AND pk.contype = 'p'
LEFT JOIN pg_constraint uk ON uk.conrelid = c.oid AND a.attnum = ANY(uk.conkey) AND uk.contype = 'u'
WHERE c.relkind = 'r'
    AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
    AND ($1::text IS NULL OR n.nspname = $1)
    AND ($2::text IS NULL OR c.relname = $2)
ORDER BY n.nspname, c.relname, a.attnum
LIMIT COALESCE($3::int, 100);
"""

LIST_TABLES = """
SELECT
    n.nspname AS schema_name,
    c.relname AS table_name,
    pg_catalog.pg_get_userbyid(c.relowner) AS owner,
    c.reltuples::bigint AS estimated_rows,
    pg_total_relation_size(c.oid) AS total_size_bytes,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    obj_description(c.oid, 'pg_class') AS comment
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
    AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
    AND n.nspname NOT LIKE 'pg_temp_%'
    AND ($1::text IS NULL OR n.nspname = $1)
ORDER BY n.nspname, c.relname
LIMIT COALESCE($2::int, 200);
"""

LIST_LOGICAL_DATABASES = """
SELECT
    d.datname AS database_name,
    pg_catalog.pg_get_userbyid(d.datdba) AS owner,
    pg_encoding_to_char(d.encoding) AS encoding,
    d.datcollate AS collation,
    d.datistemplate AS is_template,
    d.datallowconn AS allow_connections,
    pg_database_size(d.oid) AS size_bytes,
    pg_size_pretty(pg_database_size(d.oid)) AS size
FROM pg_database d
WHERE d.datistemplate = false
    AND d.datname NOT IN ('rdsadmin', 'cloudsqladmin')
ORDER BY d.datname;
"""
