---
name: ssh-logs-mcp
description: Inspect application logs on remote Linux hosts read-only over SSH through a code-enforced command allowlist. Use for errors, stack traces, trace IDs, time windows, and archived (gzip) logs. Never use it for server changes, restarts, uploads, or configuration edits.
---

# Remote Log Inspector

Read-only remote log inspection via the `ssh_logs` MCP tools. Every remote
command passes a code-enforced allowlist; out-of-bounds commands are rejected.

## Prerequisites

Install and register the MCP server (see the package README). Connection
configuration lives outside the repository
(`~/.config/ssh-logs-mcp/servers.json` or `SSH_LOGS_CONFIG`). If the `ssh_logs`
tools are not visible in this session, tell the user the host must be restarted.
Never paste credentials into chat.

## Workflow

1. Confirm the environment (alias), service, and a time range, trace ID, request
   ID, or distinctive error. Ask for missing scope when needed.
2. Use `list_logs` to see available files, then `tail_log` for the latest lines.
3. Use `grep_log` for a term (optionally ignore-case and context lines); follow a
   trace ID across services with bounded output.
4. Use `zgrep_log` for gzip archives.
5. Report matches, timestamps, IDs, key stack frames, evidence, and uncertainty.
   Do not invent a root cause when the logs are insufficient.

## Safety

- Only read-only commands are permitted:
  `tail`/`head`/`grep`/`zgrep`/`zcat`/`ls`/`wc`/`cat`.
- No shell chaining (`;`, `&&`, `||`), redirects, backticks, or `$()`; no path
  traversal; `cat`/`zcat` must be bounded by `head`/`tail`.
- Production environments are disabled by default (`forbidden`) and require
  explicit, read-only authorization.
- Never print credentials, or full secret-bearing log lines when a redacted
  excerpt is sufficient.

## Configuration

Environments are defined in the operator's external config file. Each entry
supplies the host and either a password or an SSH key, plus an optional
`forbidden` flag.
