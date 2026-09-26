# agent-safe-tools

[![CI](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

Ask your AI coding agent, in natural language, to search production logs or
inspect a database — safely. Works with any MCP-capable host (Codex, Claude
Code, OpenCode, Cursor, ...).

**Core idea: keep the safety red lines in code, not in a prompt.** Instead of
trusting the model to obey instructions, the limits are enforced by validation
and covered by unit tests.

[English](./README.md) | [简体中文](./README.zh-CN.md)

## Packages

| Package | Description | Install |
|---|---|---|
| [`safe-mysql-mcp`](./safe-mysql-mcp) | Read-only-by-default MySQL MCP server with SQL guardrails | `pip install -e ./safe-mysql-mcp` |
| [`ssh-logs-mcp`](./ssh-logs-mcp) | Read-only remote log inspection MCP server with a code-enforced command allowlist | `pip install -e ./ssh-logs-mcp` |

The two packages are independent and can also be published as separate repositories.

Each package's core is an **MCP server**; it also ships a `skill/` layer that is
**recommended** to install on skill-capable hosts (Codex / Claude Code), so the
model knows when and how to call the tools.

## Quick start

```bash
git clone https://github.com/wangke-112/agent-safe-tools.git
cd agent-safe-tools

# MySQL (read-only)
pip install -e ./safe-mysql-mcp
export MYSQL_HOST=127.0.0.1 MYSQL_USER=readonly_user MYSQL_PASSWORD=****** MYSQL_DATABASE=app
safe-mysql-mcp

# Remote logs (read-only)
pip install -e ./ssh-logs-mcp
export SSH_LOGS_CONFIG=~/.config/ssh-logs-mcp/servers.json
ssh-logs-mcp
```

Host integration snippets (Codex / Claude Code / OpenCode / Cursor) are in each
package README.

## Repository layout

```text
agent-safe-tools/
├── safe-mysql-mcp/
│   ├── src/safe_mysql_mcp/     # guard / config / db / server
│   ├── examples/               # profiles and MCP config templates
│   └── tests/                  # SQL guardrail tests (pure functions, no DB)
├── ssh-logs-mcp/
│   ├── src/ssh_logs_mcp/       # policy / config / transport / server
│   ├── examples/               # servers.json template
│   └── tests/                  # command policy tests (no SSH)
└── .github/workflows/ci.yml    # CI across multiple Python versions
```

## Why "safe"

Letting an agent connect straight to production databases or run remote shell
commands is risky. Most existing MCP servers only handle "connecting" and leave
safety to the model's prompt. This project encodes the limits:

- **Read-only by default**, DDL / dangerous statements blocked, `LIMIT` injected
  automatically, writes must carry a `WHERE` clause;
- **Command allowlist**, no `;` / `&&` / redirects / backticks / `$()`, no path
  traversal;
- **Production disabled by default** and must be enabled explicitly;
- **Credentials use environment variables or local key/config stores**, never
  inline passwords in a committed profile example;
- **SSH paths are confined to the configured log root** and host keys are
  checked through `known_hosts` or an explicit fingerprint.

All of these rules are pure functions with unit tests.

## Tests

```bash
# Run each package separately (they are independent)
cd safe-mysql-mcp && pip install -e ".[dev]" && pytest
cd ../ssh-logs-mcp && pip install -e ".[dev]" && pytest
```

## License

[MIT](./LICENSE)
