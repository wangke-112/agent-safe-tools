import pytest

from safe_mysql_mcp.guard import (
    SqlGuardError,
    apply_limit,
    check_schema_allowed,
    guard_sql,
    guard_where,
    is_read_query,
    qualified_table,
)


def test_readonly_allows_select():
    assert guard_sql("SELECT 1", read_only=True) == "SELECT 1"


def test_readonly_blocks_write():
    with pytest.raises(SqlGuardError):
        guard_sql("UPDATE t SET a = 1 WHERE id = 1", read_only=True)
    with pytest.raises(SqlGuardError):
        guard_sql("DELETE FROM t WHERE id = 1", read_only=True)


def test_blocks_ddl_and_admin():
    for sql in (
        "DROP TABLE t",
        "TRUNCATE TABLE t",
        "ALTER TABLE t ADD c INT",
        "CREATE TABLE t (id INT)",
        "GRANT ALL ON *.* TO 'x'@'%'",
        "LOAD DATA INFILE 'x' INTO TABLE t",
    ):
        with pytest.raises(SqlGuardError):
            guard_sql(sql, read_only=False)


def test_blocks_multi_statement():
    with pytest.raises(SqlGuardError):
        guard_sql("SELECT 1; DROP TABLE t", read_only=False)


def test_blocks_comments():
    for sql in ("SELECT 1 -- x", "SELECT 1 # x", "SELECT /* x */ 1"):
        with pytest.raises(SqlGuardError):
            guard_sql(sql, read_only=True)


def test_update_requires_where():
    with pytest.raises(SqlGuardError):
        guard_sql("UPDATE t SET a = 1", read_only=False)
    assert guard_sql("UPDATE t SET a = 1 WHERE id = 1", read_only=False)


def test_apply_limit():
    assert apply_limit("SELECT * FROM t", None).endswith("LIMIT 100")
    assert apply_limit("SELECT * FROM t", 5000).endswith("LIMIT 1000")
    assert apply_limit("SELECT * FROM t", 25).endswith("LIMIT 25")
    assert apply_limit("SELECT * FROM t LIMIT 5", None).endswith("LIMIT 5")
    assert apply_limit("SHOW TABLES", None) == "SHOW TABLES"


def test_identifier_and_qualified_table():
    assert qualified_table("db.t", None, "x") == "`db`.`t`"
    assert qualified_table("t", None, "db") == "`db`.`t`"
    with pytest.raises(SqlGuardError):
        qualified_table("t; DROP", None, "db")
    with pytest.raises(SqlGuardError):
        qualified_table("t", None, None)


def test_guard_where():
    assert guard_where("id = 1") == "id = 1"
    assert guard_where(None) == ""
    with pytest.raises(SqlGuardError):
        guard_where("id = 1 OR (SELECT 1)")
    with pytest.raises(SqlGuardError):
        guard_where("id = 1; DROP TABLE t")


def test_schema_allowlist():
    check_schema_allowed("app", ("app", "app2"))
    check_schema_allowed("anything", ())
    with pytest.raises(SqlGuardError):
        check_schema_allowed("secret", ("app",))


def test_is_read_query():
    assert is_read_query("WITH x AS (SELECT 1) SELECT * FROM x")
    assert is_read_query("EXPLAIN SELECT 1")
    assert not is_read_query("INSERT INTO t VALUES (1)")
