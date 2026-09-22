"""FastMCP server exposing guarded MySQL tools.

Every tool routes through :mod:`safe_mysql_mcp.guard`; nothing executes raw
caller input directly.
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import db
from .config import Profile, list_profile_names, load_profile
from .guard import (
    apply_limit,
    check_schema_allowed,
    effective_limit,
    first_keyword,
    guard_sql,
    guard_where,
    identifier,
    is_read_query,
    qualified_table,
    split_table,
)

mcp = FastMCP(os.getenv("MCP_SERVER_NAME", "safe-mysql"))


def _profile(name: str | None = None) -> Profile:
    return load_profile(name)


@mcp.tool(description="List the configured MySQL profiles.")
def mysql_list_profiles() -> dict[str, Any]:
    return {"profiles": list_profile_names()}


@mcp.tool(description="Check whether the configured MySQL database is reachable.")
def mysql_ping(profile: str | None = None) -> dict[str, Any]:
    p = _profile(profile)
    result = db.execute(p, "SELECT 1 AS ok, DATABASE() AS database_name, VERSION() AS version")
    return {
        "ok": True,
        "profile": p.name,
        "host": p.host,
        "port": p.port,
        "database": p.database,
        "read_only": p.read_only,
        "result": result["rows"][0] if result["rows"] else None,
    }


@mcp.tool(description="Show the current MySQL connection context.")
def mysql_current_database(profile: str | None = None) -> dict[str, Any]:
    p = _profile(profile)
    return db.execute(
        p, "SELECT DATABASE() AS database_name, USER() AS user_name, VERSION() AS version"
    )


@mcp.tool(
    description=(
        "Execute a guarded read-only SQL query. Use %s placeholders and pass params as a "
        "JSON array. SELECT/WITH get a default LIMIT when absent."
    )
)
def mysql_query(
    sql: str,
    params: list[Any] | None = None,
    limit: int | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    p = _profile(profile)
    guarded = guard_sql(sql, read_only=True)
    final_sql = apply_limit(
        guarded, limit, default_limit=p.default_limit, max_limit=p.max_limit
    )
    return db.execute(p, final_sql, params)


@mcp.tool(
    description=(
        "Execute a guarded write statement. Requires a writable profile; "
        "UPDATE/DELETE must include WHERE."
    )
)
def mysql_execute(
    sql: str,
    params: list[Any] | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    p = _profile(profile)
    guarded = guard_sql(sql, read_only=p.read_only)
    if is_read_query(guarded):
        raise ValueError("Use mysql_query for read statements")
    return db.execute(p, guarded, params, fetch=False)


@mcp.tool(description="Run EXPLAIN for a MySQL SELECT/WITH query.")
def mysql_explain(
    sql: str,
    params: list[Any] | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    p = _profile(profile)
    guarded = guard_sql(sql, read_only=True)
    if first_keyword(guarded) not in {"select", "with"}:
        raise ValueError("Only SELECT/WITH can be explained")
    return db.execute(p, f"EXPLAIN {guarded}", params)


@mcp.tool(description="List databases/schemas, optionally filtered with a LIKE pattern.")
def mysql_list_databases(
    pattern: str | None = None, profile: str | None = None
) -> dict[str, Any]:
    p = _profile(profile)
    sql = "SELECT SCHEMA_NAME AS schema_name FROM INFORMATION_SCHEMA.SCHEMATA"
    params: list[Any] = []
    if pattern:
        sql += " WHERE SCHEMA_NAME LIKE %s"
        params.append(pattern)
    sql += " ORDER BY SCHEMA_NAME"
    result = db.execute(p, sql, params)
    if p.allowed_schemas:
        result["rows"] = [
            row for row in result["rows"] if row.get("schema_name") in p.allowed_schemas
        ]
    return result


@mcp.tool(description="List tables/views in a schema, optionally filtered with a LIKE pattern.")
def mysql_list_tables(
    schema: str | None = None,
    pattern: str | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    p = _profile(profile)
    schema_name = schema or p.database
    if not schema_name:
        raise ValueError("A schema is required")
    identifier(schema_name)
    check_schema_allowed(schema_name, p.allowed_schemas)
    sql = """
        SELECT TABLE_SCHEMA AS table_schema, TABLE_NAME AS table_name, TABLE_TYPE AS table_type,
               ENGINE AS engine, TABLE_ROWS AS estimated_rows, CREATE_TIME AS create_time,
               UPDATE_TIME AS update_time, TABLE_COMMENT AS table_comment
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = %s
    """
    params: list[Any] = [schema_name]
    if pattern:
        sql += " AND TABLE_NAME LIKE %s"
        params.append(pattern)
    sql += " ORDER BY TABLE_NAME"
    return db.execute(p, sql, params)


@mcp.tool(description="List columns for a table or schema.table.")
def mysql_list_columns(
    table: str, schema: str | None = None, profile: str | None = None
) -> dict[str, Any]:
    p = _profile(profile)
    schema_name, table_name = split_table(table, schema, default_schema=p.database)
    check_schema_allowed(schema_name, p.allowed_schemas)
    sql = """
        SELECT ORDINAL_POSITION AS ordinal_position, COLUMN_NAME AS column_name,
               COLUMN_TYPE AS column_type, DATA_TYPE AS data_type, IS_NULLABLE AS is_nullable,
               COLUMN_DEFAULT AS column_default, COLUMN_KEY AS column_key, EXTRA AS extra,
               COLUMN_COMMENT AS column_comment
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
    """
    return db.execute(p, sql, [schema_name, table_name])


@mcp.tool(description="Describe a table using DESCRIBE table.")
def mysql_describe_table(
    table: str, schema: str | None = None, profile: str | None = None
) -> dict[str, Any]:
    p = _profile(profile)
    schema_name, _ = split_table(table, schema, default_schema=p.database)
    check_schema_allowed(schema_name, p.allowed_schemas)
    return db.execute(p, f"DESCRIBE {qualified_table(table, schema, p.database)}")


@mcp.tool(description="List indexes for a table or schema.table.")
def mysql_list_indexes(
    table: str, schema: str | None = None, profile: str | None = None
) -> dict[str, Any]:
    p = _profile(profile)
    schema_name, table_name = split_table(table, schema, default_schema=p.database)
    check_schema_allowed(schema_name, p.allowed_schemas)
    sql = """
        SELECT INDEX_NAME AS index_name, NON_UNIQUE AS non_unique, SEQ_IN_INDEX AS seq_in_index,
               COLUMN_NAME AS column_name, COLLATION AS collation, CARDINALITY AS cardinality,
               INDEX_TYPE AS index_type, COMMENT AS comment
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ORDER BY INDEX_NAME, SEQ_IN_INDEX
    """
    return db.execute(p, sql, [schema_name, table_name])


@mcp.tool(description="Show the CREATE TABLE statement for a table or schema.table.")
def mysql_show_create_table(
    table: str, schema: str | None = None, profile: str | None = None
) -> dict[str, Any]:
    p = _profile(profile)
    schema_name, _ = split_table(table, schema, default_schema=p.database)
    check_schema_allowed(schema_name, p.allowed_schemas)
    return db.execute(p, f"SHOW CREATE TABLE {qualified_table(table, schema, p.database)}")


@mcp.tool(description="Return table metadata: columns and indexes.")
def mysql_table_info(
    table: str, schema: str | None = None, profile: str | None = None
) -> dict[str, Any]:
    p = _profile(profile)
    schema_name, table_name = split_table(table, schema, default_schema=p.database)
    check_schema_allowed(schema_name, p.allowed_schemas)
    table_sql = """
        SELECT TABLE_SCHEMA AS table_schema, TABLE_NAME AS table_name, TABLE_TYPE AS table_type,
               ENGINE AS engine, TABLE_ROWS AS estimated_rows, DATA_LENGTH AS data_length,
               INDEX_LENGTH AS index_length, CREATE_TIME AS create_time,
               UPDATE_TIME AS update_time, TABLE_COMMENT AS table_comment
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
    """
    return {
        "table": db.execute(p, table_sql, [schema_name, table_name])["rows"],
        "columns": mysql_list_columns(table_name, schema_name, profile)["rows"],
        "indexes": mysql_list_indexes(table_name, schema_name, profile)["rows"],
    }


@mcp.tool(
    description="Count rows in a table, with an optional simple WHERE condition and %s params."
)
def mysql_table_count(
    table: str,
    schema: str | None = None,
    where: str | None = None,
    params: list[Any] | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    p = _profile(profile)
    schema_name, _ = split_table(table, schema, default_schema=p.database)
    check_schema_allowed(schema_name, p.allowed_schemas)
    condition = guard_where(where)
    sql = f"SELECT COUNT(*) AS row_count FROM {qualified_table(table, schema, p.database)}"
    if condition:
        sql += f" WHERE {condition}"
    return db.execute(p, sql, params)


@mcp.tool(description="Sample rows from a table, with an optional simple WHERE condition.")
def mysql_sample_table(
    table: str,
    schema: str | None = None,
    where: str | None = None,
    params: list[Any] | None = None,
    limit: int | None = 20,
    profile: str | None = None,
) -> dict[str, Any]:
    p = _profile(profile)
    schema_name, _ = split_table(table, schema, default_schema=p.database)
    check_schema_allowed(schema_name, p.allowed_schemas)
    condition = guard_where(where)
    sql = f"SELECT * FROM {qualified_table(table, schema, p.database)}"
    if condition:
        sql += f" WHERE {condition}"
    value = effective_limit(
        limit, default_limit=p.default_limit, max_limit=p.max_limit
    )
    sql += f" LIMIT {value}"
    return db.execute(p, sql, params)


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
