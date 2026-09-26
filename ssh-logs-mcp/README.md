# ssh-logs-mcp

[![CI](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

Ask your AI coding agent, in natural language, to search service logs on remote
hosts — safely. This is a **read-only** remote log inspection MCP server for any
MCP-capable host (Codex / Claude Code / OpenCode / Cursor).

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
- **Log root isolation** — structured tools can only access paths below each environment's configured `log_root`.
- **SSH host verification** — trust a `known_hosts` entry or pin a SHA256 host-key fingerprint; unknown keys fail closed.
- **Credentials never committed** — SSH passwords are read from environment variables; SSH keys are supported. Inline passwords are rejected.

## Install

Not published to PyPI — install from source:

```bash
git clone https://github.com/wangke-112/agent-safe-tools.git
pip install -e agent-safe-tools/ssh-logs-mcp

# or, if you are already inside the repo:
pip install -e .
```

## Configuration

Default path `~/.config/ssh-logs-mcp/servers.json`, overridable with
`SSH_LOGS_CONFIG`.

See [`examples/servers.example.json`](./examples/servers.example.json). Set the referenced
password environment variable in the MCP host process, or use `key_path`.

```json
{
  "envs": {
    "test": {
      "desc": "internal test host",
      "host": "10.0.0.10",
      "port": 22,
      "user": "reader",
      "password_env": "SSH_TEST_PASSWORD",
      "log_root": "/var/log/my-service",
      "known_hosts": "~/.ssh/known_hosts"
    },
    "prd": {
      "desc": "production (disabled by default)",
      "host": "10.0.0.20",
      "port": 22,
      "user": "reader",
      "password_env": "SSH_PRD_PASSWORD",
      "log_root": "/var/log/my-service",
      "known_hosts": "~/.ssh/known_hosts",
      "forbidden": true
    }
  }
}
```

`run_readonly` is intentionally disabled because arbitrary command arguments
cannot be proven to stay within `log_root`; use the structured tools instead.

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
| Log-path containment | `policy.ensure_log_path` (structured tools) |
| Unknown SSH host keys rejected / SHA256 pinning | `transport._FingerprintPolicy` |
| Inline SSH passwords rejected | `config.get_env` |
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

- Path isolation is lexical and cannot detect remote symlinks beneath `log_root`;
  configure the root so untrusted users cannot create symlinks inside it.
- Command validation is an allowlist plus forbidden-substring check, not a full
  shell parser, but it covers common injection techniques;
- For safety, the `pattern` argument of `grep_log` / `zgrep_log` does not accept
  complex regex characters such as `|`, `()`, `$`; use `run_readonly` for
  complex pipelines (also validated by the allowlist);
- Line-based log commands only; no `journalctl` or other system log sources.

## License

MIT
