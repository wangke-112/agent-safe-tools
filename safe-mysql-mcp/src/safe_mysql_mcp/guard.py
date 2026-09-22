"""Pure, side-effect-free SQL guardrails.

Every function here is intentionally free of I/O so the safety rules can be
unit tested without a database. This is the core value of the project: the
"red lines" live in code, not in a prompt.
"""

from __future__ import annotations

import re

READ_KEYWORDS = {"select", "show", "describe", "desc", "explain", "with"}

_IDENT = re.compile(r"^[A-Za-z0-9_$]+$")

_FORBIDDEN_SQL = re.compile(
    r"\b(drop|truncate|alter|create|rename|grant|revoke|shutdown|kill|flush|"
    r"reset|outfile|infile)\b|\bload\s+data\b",
    re.IGNORECASE,
)

_WHERE_FORBIDDEN = re.compile(
    r"\b(select|insert|update|delete|replace|call)\b", re.IGNORECASE
)


class SqlGuardError(ValueError):
    """Raised when a statement violates the configured policy."""


def clean_sql(sql: str) -> str:
    """Reject empty input, multiple statements and SQL comments."""

    if not sql or not sql.strip():
        raise SqlGuardError("SQL must not be empty")
    stripped = sql.strip().lstrip("\ufeff")
    while stripped.endswith(";"):
        stripped = stripped[:-1].rstrip()
    if ";" in stripped:
        raise SqlGuardError("Multiple SQL statements are blocked")
    if "/*" in stripped or "--" in stripped or "#" in stripped:
        raise SqlGuardError("SQL comments are blocked in guarded execution")
    return stripped


def first_keyword(sql: str) -> str:
    match = re.match(r"^\s*([A-Za-z]+)", sql)
    return match.group(1).lower() if match else ""


def is_read_query(sql: str) -> bool:
    return first_keyword(sql) in READ_KEYWORDS


def guard_sql(sql: str, *, read_only: bool = True) -> str:
    """Apply the full statement policy and return the cleaned SQL."""

    cleaned = clean_sql(sql)
    normalized = re.sub(r"\s+", " ", cleaned.lower())
    if _FORBIDDEN_SQL.search(normalized):
        raise SqlGuardError("DDL/admin/file SQL is blocked by this server")
    if read_only and not is_read_query(cleaned):
        allowed = "/".join(sorted(READ_KEYWORDS))
        raise SqlGuardError(f"This profile is read-only; only {allowed} are allowed")
    if re.match(r"^\s*(update|delete)\b", cleaned, re.IGNORECASE) and not re.search(
        r"\bwhere\b", normalized
    ):
        raise SqlGuardError("UPDATE/DELETE without WHERE is blocked")
    return cleaned


def guard_where(where: str | None) -> str:
    """Validate a caller-supplied WHERE fragment."""

    if not where:
        return ""
    cleaned = clean_sql(where)
    normalized = re.sub(r"\s+", " ", cleaned.lower())
    if _FORBIDDEN_SQL.search(normalized) or _WHERE_FORBIDDEN.search(normalized):
        raise SqlGuardError("Unsafe WHERE condition is blocked")
    return cleaned


def effective_limit(
    limit: int | None, *, default_limit: int = 100, max_limit: int = 1000
) -> int:
    value = default_limit if limit is None else int(limit)
    if value < 1:
        value = 1
    return min(value, max_limit)


def apply_limit(
    sql: str, limit: int | None, *, default_limit: int = 100, max_limit: int = 1000
) -> str:
    """Append a LIMIT to SELECT/WITH statements that do not already have one."""

    if first_keyword(sql) not in {"select", "with"}:
        return sql
    if re.search(r"\blimit\s+\d+\b", sql, flags=re.IGNORECASE):
        return sql
    value = effective_limit(limit, default_limit=default_limit, max_limit=max_limit)
    return f"{sql} LIMIT {value}"


def identifier(part: str) -> str:
    if not part or not _IDENT.match(part):
        raise SqlGuardError(f"Invalid identifier: {part!r}")
    return f"`{part}`"


def split_table(
    table: str, schema: str | None = None, default_schema: str | None = None
) -> tuple[str, str]:
    if not table or not table.strip():
        raise SqlGuardError("Table name must not be empty")
    parts = [p.strip(" `") for p in table.split(".")]
    if len(parts) == 2:
        schema_name, table_name = parts
    elif len(parts) == 1:
        schema_name, table_name = (schema or default_schema), parts[0]
    else:
        raise SqlGuardError("Use table or schema.table")
    if not schema_name:
        raise SqlGuardError("Schema/database is required")
    if not _IDENT.match(schema_name) or not _IDENT.match(table_name):
        raise SqlGuardError("Invalid schema or table name")
    return schema_name, table_name


def qualified_table(
    table: str, schema: str | None = None, default_schema: str | None = None
) -> str:
    schema_name, table_name = split_table(table, schema, default_schema)
    return f"{identifier(schema_name)}.{identifier(table_name)}"


def check_schema_allowed(schema_name: str, allowed: tuple[str, ...]) -> None:
    if allowed and schema_name not in allowed:
        raise SqlGuardError(f"Schema '{schema_name}' is not in the allowed list")
