import pytest

from ssh_logs_mcp.policy import (
    CommandPolicyError,
    ensure_glob,
    ensure_safe_input,
    validate_command,
)


def test_allows_safe_pipelines():
    assert validate_command("tail -n 200 /var/log/app.log")
    assert validate_command("grep -n -e 'ERROR' /var/log/app.log | head -n 50")
    assert validate_command("zgrep 'x' /var/log/a-2026-01-01.log.gz | head -n 10")
    assert validate_command("ls -lh /var/log | head -n 100")


def test_blocks_disallowed_commands():
    for cmd in ("rm -rf /", "sed -i s/a/b/ f", "bash -c 'rm x'", "cat /var/log/app.log"):
        with pytest.raises(CommandPolicyError):
            validate_command(cmd)


def test_blocks_shell_metacharacters():
    for cmd in (
        "tail -n 1 /a; rm -rf /",
        "ls /a > /tmp/x",
        "cat `ls`",
        "ls $(rm)",
        "ls /a && rm /b",
        "ls /a || rm /b",
        "tail -n 1 ../../etc/passwd",
    ):
        with pytest.raises(CommandPolicyError):
            validate_command(cmd)


def test_cat_must_be_bounded():
    with pytest.raises(CommandPolicyError):
        validate_command("cat /var/log/app.log")
    assert validate_command("cat /var/log/app.log | head -n 100")


def test_blocks_recursive_and_file_grep():
    with pytest.raises(CommandPolicyError):
        validate_command("grep -r foo /var/log")
    with pytest.raises(CommandPolicyError):
        validate_command("grep --file patterns.txt /var/log/app.log")


def test_blocks_tail_follow():
    with pytest.raises(CommandPolicyError):
        validate_command("tail -f /var/log/app.log")


def test_ensure_safe_input():
    assert ensure_safe_input("/var/log/app.log", what="path") == "/var/log/app.log"
    for bad in ("a;b", "a|b", "a$(b)", "a`b`", "../etc", ""):
        with pytest.raises(CommandPolicyError):
            ensure_safe_input(bad, what="value")


def test_ensure_glob():
    assert ensure_glob("*.log")
    assert ensure_glob("order-2026-*.log.gz")
    with pytest.raises(CommandPolicyError):
        ensure_glob("*.log; rm -rf /")
    with pytest.raises(CommandPolicyError):
        ensure_glob("a b")
import pytest

from ssh_logs_mcp.policy import CommandPolicyError, ensure_log_path


def test_log_path_is_confined_to_root():
    assert ensure_log_path("app/service.log", "/var/log") == "/var/log/app/service.log"
    assert ensure_log_path("/var/log/app/service.log", "/var/log") == "/var/log/app/service.log"


@pytest.mark.parametrize("path", ["/etc/passwd", "../secrets", "app/../../etc/passwd", "/var/log-old/app.log"])
def test_log_path_rejects_escape(path):
    with pytest.raises(CommandPolicyError):
        ensure_log_path(path, "/var/log")


def test_log_root_must_be_absolute():
    with pytest.raises(CommandPolicyError):
        ensure_log_path("app.log", "var/log")
