# ssh-logs-mcp

[![CI](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

A **read-only** remote log inspection MCP server. It lets AI agents
(Codex / Claude Code / OpenCode / Cursor, or any MCP-capable host) search
service logs on remote hosts safely.

> Many "log query" solutions put the safety rules in a prompt and trust the
> model. `ssh-logs-mcp` **encodes the command allowlist, no-redirect and
> no-chaining rules in code** — out-of-bounds commands are rejected, and the
> rules are unit tested.

[English](./README.md) | [简体中文](./README.zh-CN.md)

> **Layout:** the core of this project is an **MCP server**. `skill/` is a
> **recommended** Skill layer for skill-capable hosts (Codex / Claude Code).

## Features

- **Command allowlist** — only `tail / head / grep / zgrep / zcat / ls / wc / cat`.
- **Dangerous syntax blocked** — `;`, `&&`, `||`, `>`, `<`, backticks, `$()`, `..`.
- **Streaming commands must be bounded** — `cat` / `zcat` must be limited by `head` / `tail`.
- **grep hardening** — `--file` and recursive `-r/-R` blocked; `tail -f` blocked.
- **Multiple environments** — `pre` / `test` / `prd` ... each with its own host and credentials.
- **Production disabled by default** — an environment marked `forbidden` refuses to connect until explicitly enabled.
- **CJK decoding** — UTF-8 → GBK fallback to avoid mojibake.
- **Credentials never committed** — read from a user-owned config file; SSH keys supported.

## Install

```bash
pip install ssh-logs-mcp
# or from source
pip install -e .
```

## Configuration

Default path `~/.config/ssh-logs-mcp/servers.json`, overridable with
`SSH_LOGS_CONFIG`.

See [`examples/servers.example.json`](./examples/servers.example.json):

```json
{
  "envs": {
    "test": {
      "desc": "internal test host",
      "host": "10.0.0.10",
      "port": 22,
      "user": "reader",
      "password": "CHANGE_ME"
    },
    "prd": {
      "desc": "production (disabled by default)",
      "host": "10.0.0.20",
      "port": 22,
      "user": "reader",
      "password": "CHANGE_ME",
      "forbidden": true
    }
  }
}
```

Use `key_path` instead of `password` for SSH key authentication.

## Host integration

**Codex (`~/.codex/config.toml`)**

```toml
[mcp_servers.ssh_logs]
type = "stdio"
command = "ssh-logs-mcp"
```

**Claude Code / OpenCode / Cursor (MCP JSON)**

```json
{ "mcpServers": { "ssh_logs": { "command": "ssh-logs-mcp" } } }
```

## Install the skill (recommended)

The MCP server provides the tools; the `skill/` directory is a **recommended**
Skill layer that tells the agent when and how to use them. Without it the model
can still call the tools, but it triggers less reliably. Install it so the model
reads the workflow and safety rules:

```bash
# Codex
mkdir -p ~/.codex/skills/ssh-logs-mcp
cp -r skill/. ~/.codex/skills/ssh-logs-mcp/

# Claude Code
mkdir -p ~/.claude/skills/ssh-logs-mcp
cp -r skill/. ~/.claude/skills/ssh-logs-mcp/
```

## Tools

| Tool | Description |
|---|---|
| `list_envs` | List configured environments (including whether disabled) |
| `run_readonly` | Run an **allowlist-validated** read-only command |
| `tail_log` | Show the last N lines of a file |
| `grep_log` | Search a file (optional ignore-case and context lines) |
| `zgrep_log` | Search a gzip-compressed log archive |
| `list_logs` | List log files in a directory |

## Security model

| Rule | Enforced in |
|---|---|
| Command allowlist | `policy.validate_command` |
| No `;` / `&&` / `||` / redirects / backticks / `$()` | `policy.validate_command` |
| No path traversal `..` | `policy.validate_command` |
| `cat` / `zcat` must be bounded | `policy.validate_command` |
| `grep --file` / recursive blocked | `policy._check_options` |
| `tail -f` blocked | `policy._check_options` |
| Production disabled | `config.get_env` + `forbidden` |

## Tests

```bash
pytest
```

The command policy is a pure function, so tests need no SSH connection.

## Known limitations

- Depends on `paramiko` and uses `AutoAddPolicy` by default (no host key
  verification); production should pin a known_hosts file;
- Command validation is an allowlist plus forbidden-substring check, not a full
  shell parser, but it covers common injection techniques;
- For safety, the `pattern` argument of `grep_log` / `zgrep_log` does not accept
  complex regex characters such as `|`, `()`, `$`; use `run_readonly` for
  complex pipelines (also validated by the allowlist);
- Line-based log commands only; no `journalctl` or other system log sources.

## License

MIT
