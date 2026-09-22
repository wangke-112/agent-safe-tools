# safe-mysql-mcp

[![CI](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

A read-only-by-default MySQL MCP server that **encodes its safety rules in
code**. It lets AI agents (Codex / Claude Code / OpenCode / Cursor, or any
MCP-capable host) query databases safely.

> Most MySQL MCP servers just "connect" and leave safety to the model's prompt.
> `safe-mysql-mcp` moves the limits into code — **read-only by default, DDL
> blocked, automatic LIMIT, writes require WHERE** — and every rule is unit
> tested.

[English](./README.md) | [简体中文](./README.zh-CN.md)

## Features

- **Read-only by default** — only `SELECT / SHOW / DESCRIBE / EXPLAIN / WITH`.
- **DDL / dangerous statements blocked** — `DROP / TRUNCATE / ALTER / GRANT / LOAD DATA ...`.
- **Multi-statement and comment injection blocked** — `SELECT 1; DROP ...`, `--`, `#`, `/* */`.
- **Automatic LIMIT** — added to `SELECT` without one, capped by `max_limit`.
- **Writes require WHERE** — `UPDATE / DELETE` without `WHERE` are rejected.
- **Identifier validation** — schema/table names are whitelist-checked.
- **Multiple profiles** — one process can serve several databases, switchable via the `profile` argument; production can be read-only.
- **Schema allowlist** — restrict access to specific databases.
- **Credentials never stored** — read from environment variables or a user-owned config file.

## Install

```bash
pip install safe-mysql-mcp
# or from source
pip install -e .
```

## Configuration

### Option 1: environment variables (single database)

```bash
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_USER=readonly_user
export MYSQL_PASSWORD=******
export MYSQL_DATABASE=app
export MYSQL_READ_ONLY=true
```

### Option 2: a profiles file (multiple databases)

Default path `~/.config/safe-mysql-mcp/profiles.json`, overridable with
`SAFE_MYSQL_PROFILES`. Select the active profile with `SAFE_MYSQL_PROFILE`.

See [`examples/profiles.example.json`](./examples/profiles.example.json):

```json
{
  "profiles": {
    "local":   { "host": "127.0.0.1", "user": "readonly_user", "password": "CHANGE_ME", "database": "app", "read_only": true },
    "staging": { "host": "10.0.0.10", "user": "app_user", "password": "CHANGE_ME", "database": "app_staging", "read_only": false, "max_limit": 500 }
  }
}
```

## Host integration

**Codex (`~/.codex/config.toml`)**

```toml
[mcp_servers.safe_mysql]
type = "stdio"
command = "safe-mysql-mcp"
env = { SAFE_MYSQL_PROFILE = "local" }
```

**Claude Code / OpenCode / Cursor (MCP JSON)**

```json
{
  "mcpServers": {
    "safe_mysql": {
      "command": "safe-mysql-mcp",
      "env": { "SAFE_MYSQL_PROFILE": "local" }
    }
  }
}
```

## Install as a skill (optional)

The MCP server provides the tools; the bundled `SKILL.md` tells the agent when
and how to use them. Install it as a skill so the model reads the workflow and
safety rules:

```bash
# Codex
mkdir -p ~/.codex/skills/safe-mysql-mcp
cp -r SKILL.md agents ~/.codex/skills/safe-mysql-mcp/

# Claude Code
mkdir -p ~/.claude/skills/safe-mysql-mcp
cp -r SKILL.md agents ~/.claude/skills/safe-mysql-mcp/
```

## Tools

| Tool | Description |
|---|---|
| `mysql_ping` | Connectivity check |
| `mysql_current_database` | Current connection context |
| `mysql_query` | Read-only query (LIMIT injected automatically) |
| `mysql_execute` | Write (requires `read_only=false`; `UPDATE/DELETE` must have `WHERE`) |
| `mysql_explain` | `EXPLAIN` for `SELECT/WITH` |
| `mysql_list_databases` / `mysql_list_tables` | Database / table listing |
| `mysql_list_columns` / `mysql_describe_table` | Column structure |
| `mysql_list_indexes` / `mysql_show_create_table` / `mysql_table_info` | Index and DDL info |
| `mysql_table_count` / `mysql_sample_table` | Counting / sampling |
| `mysql_list_profiles` | List configured profiles |

Every tool accepts an optional `profile` argument to switch connections.

## Security model

| Rule | Enforced in |
|---|---|
| Read-only enforcement | `guard.guard_sql` |
| DDL / dangerous statements | `guard.guard_sql` |
| Multi-statement / comment injection | `guard.clean_sql` |
| Automatic LIMIT + cap | `guard.apply_limit` |
| Writes require WHERE | `guard.guard_sql` |
| Identifier validation | `guard.identifier` / `guard.split_table` |
| Schema allowlist | `guard.check_schema_allowed` |

## Tests

```bash
pytest
```

The guardrails are pure functions, so tests need no database connection.

## Known limitations

- MySQL only;
- Single process, one connection per profile, no connection pool;
- Write capability must be enabled explicitly via `read_only=false`; keep
  production read-only.

## License

MIT
