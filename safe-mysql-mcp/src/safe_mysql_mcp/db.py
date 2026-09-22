"""Connection and execution helpers."""

from __future__ import annotations

import base64
import datetime as dt
import decimal
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from .config import Profile


def connect(profile: Profile):
    return pymysql.connect(
        host=profile.host,
        port=profile.port,
        user=profile.user,
        password=profile.password,
        database=profile.database,
        charset=profile.charset,
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=profile.connect_timeout,
        read_timeout=profile.read_timeout,
        write_timeout=profile.write_timeout,
    )


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"base64": base64.b64encode(bytes(value)).decode("ascii")}
    return value


def execute(
    profile: Profile,
    sql: str,
    params: list[Any] | None = None,
    *,
    fetch: bool = True,
) -> dict[str, Any]:
    conn = connect(profile)
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, tuple(params) if params is not None else None)
            rows = cursor.fetchall() if fetch and cursor.description else []
            return {
                "sql": sql,
                "row_count": cursor.rowcount,
                "affected_rows": cursor.rowcount,
                "lastrowid": cursor.lastrowid,
                "columns": [d[0] for d in cursor.description] if cursor.description else [],
                "rows": jsonable(rows),
            }
    finally:
        conn.close()
