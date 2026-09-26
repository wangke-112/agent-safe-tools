"""Command policy — the heart of this project.

The allowlist and the forbidden constructs are enforced **here, in code**,
instead of being delegated to a prompt the model may ignore. Every function is
pure and therefore easy to unit test.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

ALLOWED_COMMANDS = frozenset({"tail", "head", "grep", "zgrep", "zcat", "cat", "ls", "wc"})
UNBOUNDED_STREAMERS = frozenset({"cat", "zcat"})
BOUNDING_COMMANDS = frozenset({"head", "tail"})

MAX_COMMAND_LENGTH = 4096
MAX_SEGMENTS = 6

_FORBIDDEN_SUBSTRINGS = (";", ">", "<", "`", "$", "\n", "\r", "&&", "||")
_META_INPUT = re.compile(r"[;|&<>`$()\n\r]")
_GLOB = re.compile(r"^[A-Za-z0-9_.*?\-]+$")
_RECURSIVE_FLAG = re.compile(r"^-{1,2}[A-Za-z]*[rR][A-Za-z]*$")


class CommandPolicyError(ValueError):
    """Raised when a command violates the read-only policy."""


def ensure_safe_input(value: str, *, what: str = "value") -> str:
    """Validate a value that will be embedded into a command (path, pattern)."""

    if value is None or value == "":
        raise CommandPolicyError(f"{what} must not be empty")
    if _META_INPUT.search(value):
        raise CommandPolicyError(f"{what} contains disallowed shell characters")
    if ".." in value:
        raise CommandPolicyError(f"{what} must not contain '..'")
    return value


def ensure_log_path(path: str, log_root: str) -> str:
    """Require an absolute or root-relative path to stay below log_root."""
    ensure_safe_input(path, what="path")
    ensure_safe_input(log_root, what="log_root")
    if not log_root.startswith("/"):
        raise CommandPolicyError("log_root must be an absolute POSIX path")
    root = PurePosixPath(log_root)
    candidate = PurePosixPath(path) if path.startswith("/") else root / path
    candidate = PurePosixPath(*candidate.parts)
    if not candidate.is_absolute():
        raise CommandPolicyError("log paths must be absolute or relative to log_root")
    if not candidate.is_relative_to(root):
        raise CommandPolicyError("path must stay below configured log_root")
    return candidate.as_posix()


def ensure_glob(pattern: str) -> str:
    """Allow only simple glob characters (no shell metacharacters)."""

    if not _GLOB.match(pattern):
        raise CommandPolicyError("glob pattern contains disallowed characters")
    return pattern


def _check_options(prog: str, tokens: list[str]) -> None:
    if prog in {"grep", "zgrep"}:
        for token in tokens:
            if token in {"-f", "--file"} or token.startswith("--file="):
                raise CommandPolicyError("grep --file is blocked")
            if _RECURSIVE_FLAG.match(token):
                raise CommandPolicyError("recursive grep is blocked")
    if prog == "tail":
        for token in tokens:
            if token in {"-f", "-F", "--follow"} or token.startswith("--follow="):
                raise CommandPolicyError("tail follow mode is blocked")


def validate_command(command: str) -> str:
    """Validate a raw command string against the read-only allowlist."""

    if not command or not command.strip():
        raise CommandPolicyError("command must not be empty")
    cmd = command.strip()
    if len(cmd) > MAX_COMMAND_LENGTH:
        raise CommandPolicyError("command is too long")
    for bad in _FORBIDDEN_SUBSTRINGS:
        if bad in cmd:
            raise CommandPolicyError(f"disallowed substring: {bad!r}")
    if ".." in cmd:
        raise CommandPolicyError("path traversal '..' is blocked")

    segments = [segment.strip() for segment in cmd.split("|")]
    if len(segments) > MAX_SEGMENTS:
        raise CommandPolicyError("too many pipeline stages")
    for segment in segments:
        if not segment:
            raise CommandPolicyError("empty pipeline stage")
        tokens = segment.split()
        prog = tokens[0]
        if prog not in ALLOWED_COMMANDS:
            raise CommandPolicyError(f"command not allowed: {prog}")
        _check_options(prog, tokens[1:])

    programs = [segment.split()[0] for segment in segments]
    if any(p in UNBOUNDED_STREAMERS for p in programs) and not any(
        p in BOUNDING_COMMANDS for p in programs
    ):
        raise CommandPolicyError(
            "cat/zcat must be bounded by head or tail in the pipeline"
        )
    return cmd
