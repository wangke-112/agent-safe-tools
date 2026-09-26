"""FastMCP tools for read-only remote log inspection.

Raw commands go through :func:`policy.validate_command`; the high-level tools
(path/pattern based) validate their inputs, build the command themselves with
shell quoting, and then re-run the same policy check as a defense in depth.
"""

from __future__ import annotations

import os
import shlex
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import transport
from .config import get_env, load_envs
from .policy import ensure_glob, ensure_log_path, ensure_safe_input, validate_command

mcp = FastMCP(os.getenv("MCP_SERVER_NAME", "ssh-logs"))


def _bounded(value: int, low: int, high: int) -> int:
    return max(low, min(int(value), high))


@mcp.tool(description="List configured environments (name, description, host, forbidden).")
def list_envs() -> dict[str, Any]:
    return {
        "envs": [
            {
                "name": env.name,
                "description": env.description,
                "host": env.host,
                "port": env.port,
                "forbidden": env.forbidden,
            }
            for env in load_envs().values()
        ]
    }


@mcp.tool(description="Disabled: use the structured log tools, which enforce log_root.")
def run_readonly(env: str, command: str) -> dict[str, Any]:
    raise ValueError("raw commands are disabled; use the structured log tools")


@mcp.tool(description="Show the last N lines of a log file.")
def tail_log(env: str, path: str, lines: int = 200) -> dict[str, Any]:
    server = get_env(env)
    path = ensure_log_path(path, server.log_root)
    command = f"tail -n {_bounded(lines, 1, 10000)} {shlex.quote(path)}"
    validate_command(command)
    return transport.run_command(server, command)


@mcp.tool(description="Search a log file with grep.")
def grep_log(
    env: str,
    path: str,
    pattern: str,
    context: int = 0,
    max_lines: int = 200,
    ignore_case: bool = False,
) -> dict[str, Any]:
    server = get_env(env)
    path = ensure_log_path(path, server.log_root)
    ensure_safe_input(pattern, what="pattern")
    flags = ["-n"]
    if ignore_case:
        flags.append("-i")
    if context:
        flags.append(f"-A {_bounded(context, 0, 50)}")
    command = (
        f"grep {' '.join(flags)} -e {shlex.quote(pattern)} {shlex.quote(path)} "
        f"| head -n {_bounded(max_lines, 1, 2000)}"
    )
    validate_command(command)
    return transport.run_command(server, command)


@mcp.tool(description="Search a gzip-compressed log archive with zgrep.")
def zgrep_log(
    env: str,
    path: str,
    pattern: str,
    max_lines: int = 100,
    ignore_case: bool = False,
) -> dict[str, Any]:
    server = get_env(env)
    path = ensure_log_path(path, server.log_root)
    ensure_safe_input(pattern, what="pattern")
    flags = ["-n"] + (["-i"] if ignore_case else [])
    command = (
        f"zgrep {' '.join(flags)} -e {shlex.quote(pattern)} {shlex.quote(path)} "
        f"| head -n {_bounded(max_lines, 1, 2000)}"
    )
    validate_command(command)
    return transport.run_command(server, command)


@mcp.tool(description="List log files in a directory (simple glob pattern allowed).")
def list_logs(
    env: str,
    directory: str,
    pattern: str = "*.log",
    max_lines: int = 200,
) -> dict[str, Any]:
    server = get_env(env)
    directory = ensure_log_path(directory, server.log_root)
    ensure_glob(pattern)
    command = (
        f"ls -lh {shlex.quote(directory.rstrip('/') + '/')}{pattern} "
        f"| head -n {_bounded(max_lines, 1, 2000)}"
    )
    validate_command(command)
    return transport.run_command(server, command)


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
