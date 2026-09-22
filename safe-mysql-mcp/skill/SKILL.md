---
name: safe-mysql-mcp
description: Inspect MySQL databases safely through a read-only-by-default MCP server with code-enforced SQL guardrails. Use when a task needs MySQL/MariaDB schema discovery, bounded read queries, validating SQL before running it, or EXPLAIN query plans. Do not use it as a substitute for migrations or backups.
---

# Safe MySQL MCP

A read-only-by-default MySQL MCP server whose safety rules are enforced in
code. Use the `safe_mysql` MCP tools for schema inspection and bounded read
queries. Never guess a table, column, or database name when it can be inspected
first.

## Prerequisites

Install and register the MCP server (see the package README). If the
`safe_mysql` tools are not visible in this session, tell the user the host must
be restarted so the MCP config is loaded. Never paste credentials into chat.

## Workflow

1. Identify the target profile/environment. If production versus non-production
   is ambiguous and the query could affect data, ask first.
2. Discover schema with `mysql_list_databases`, `mysql_list_tables`,
   `mysql_list_columns`, `mysql_describe_table`, `mysql_list_indexes`, or
   `mysql_show_create_table`.
3. Use bounded, parameterized reads with `mysql_query`. `SELECT`/`WITH` without
   a `LIMIT` get one automatically; prefer limited, indexed predicates.
4. Use `mysql_explain` for expensive queries instead of running them blind.
5. When generating SQL, validate it against the real schema and existing rows;
   state assumptions, expected row counts, and verification queries.

## Safety

- Read-only by default: only `SELECT`/`SHOW`/`DESCRIBE`/`EXPLAIN`/`WITH`.
- Do not run `DROP` or `TRUNCATE`; DDL is blocked by the server anyway.
- `UPDATE`/`DELETE` without a `WHERE` clause are rejected.
- Do not execute generated import or migration SQL merely because it was
  requested in prose; show it for review unless execution is explicit.
- Keep production profiles read-only unless the user explicitly authorizes a
  change.
- Never print passwords, MCP env blocks, connection strings, or credentials.

## Configuration

The server is configured by environment variables (`MYSQL_*`) or a profiles
file (`SAFE_MYSQL_PROFILES` / `SAFE_MYSQL_PROFILE`). Keep credentials outside
this skill directory.
