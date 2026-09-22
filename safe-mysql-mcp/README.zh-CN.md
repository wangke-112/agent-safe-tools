# safe-mysql-mcp

[![CI](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

用自然语言让 AI 编码助手安全地查询 MySQL 数据库。一个默认只读、**把安全护栏写进代码**的 MySQL MCP Server，供任何 MCP 宿主（Codex / Claude Code / OpenCode / Cursor 等）使用。

> 大多数 MySQL MCP Server 只负责"连上"，把安全交给模型自觉遵守提示词。
> `safe-mysql-mcp` 把限制下沉到代码：**只读强制、DDL 拦截、自动补 LIMIT、写操作必须有 WHERE**，并且这些规则全部可单元测试。

[English](./README.md) | [简体中文](./README.zh-CN.md)

> **定位**：本项目核心是 **MCP Server**；`skill/` 是**建议安装**的 Skill 适配层，供支持 Skill 的宿主（Codex / Claude Code）使用。

## 特性

- **默认只读**：只有 `SELECT / SHOW / DESCRIBE / EXPLAIN / WITH` 能执行。
- **DDL / 危险语句拦截**：`DROP / TRUNCATE / ALTER / GRANT / LOAD DATA ...` 直接拒绝。
- **防多语句与注释注入**：`SELECT 1; DROP ...`、`--` / `#` / `/* */` 一律拦截。
- **自动 LIMIT**：`SELECT` 未带 `LIMIT` 时自动补，并受 `max_limit` 约束。
- **写操作必须有 WHERE**：`UPDATE / DELETE` 不带 `WHERE` 拒绝。
- **标识符校验**：库名 / 表名白名单正则，防止注入式标识符。
- **多 profile**：一个进程可配置多个库（本地 / 测试 / 生产），用 `profile` 参数切换，生产可单独设为只读。
- **schema 白名单**：可限制只允许访问指定库。
- **凭证不落盘**：从环境变量或用户目录下的配置文件读取。

## 安装

未发布到 PyPI，从源码安装：

```bash
git clone https://github.com/wangke-112/agent-safe-tools.git
pip install -e agent-safe-tools/safe-mysql-mcp

# 或已在仓库内：
pip install -e .
```

## 配置

### 方式一：环境变量（单库，最简）

```bash
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_USER=readonly_user
export MYSQL_PASSWORD=******
export MYSQL_DATABASE=app
export MYSQL_READ_ONLY=true
```

### 方式二：profiles 文件（多库）

默认路径 `~/.config/safe-mysql-mcp/profiles.json`，可用环境变量 `SAFE_MYSQL_PROFILES` 覆盖。
用 `SAFE_MYSQL_PROFILE` 选择当前 profile。

参考 [`examples/profiles.example.json`](./examples/profiles.example.json)：

```json
{
  "profiles": {
    "local":   { "host": "127.0.0.1", "user": "readonly_user", "password": "CHANGE_ME", "database": "app",  "read_only": true },
    "staging": { "host": "10.0.0.10", "user": "app_user",     "password": "CHANGE_ME", "database": "app_staging", "read_only": false, "max_limit": 500 }
  }
}
```

## 在各宿主里接入

**Codex（`~/.codex/config.toml`）**

```toml
[mcp_servers.safe_mysql]
type = "stdio"
command = "safe-mysql-mcp"
env = { SAFE_MYSQL_PROFILE = "local" }
```

**Claude Code / OpenCode / Cursor（MCP JSON）**

```json
{
  "mcpServers": {
    "safe_mysql": {
      "command": "safe-mysql-mcp",
      "env": { "SAFE_MYSQL_PROFILE": "local" }
    }
  }
}
```

## 安装 Skill（建议安装）

MCP 提供工具，`skill/` 目录是**建议安装**的 Skill 层，告诉模型什么时候用、怎么用、红线是什么。只装 MCP 时模型仍能调用，但**触发没那么可靠**；装上 Skill 后模型会读工作流与安全规则：

```bash
# Codex
mkdir -p ~/.codex/skills/safe-mysql-mcp
cp -r skill/. ~/.codex/skills/safe-mysql-mcp/

# Claude Code
mkdir -p ~/.claude/skills/safe-mysql-mcp
cp -r skill/. ~/.claude/skills/safe-mysql-mcp/
```

## 暴露的工具

| 工具 | 说明 |
|---|---|
| `mysql_ping` | 连通性检查 |
| `mysql_current_database` | 当前连接上下文 |
| `mysql_query` | 只读查询（自动补 LIMIT） |
| `mysql_execute` | 写操作（需 `read_only=false`，且 `UPDATE/DELETE` 必须带 `WHERE`） |
| `mysql_explain` | 对 `SELECT/WITH` 执行 `EXPLAIN` |
| `mysql_list_databases` / `mysql_list_tables` | 库 / 表列表 |
| `mysql_list_columns` / `mysql_describe_table` | 列结构 |
| `mysql_list_indexes` / `mysql_show_create_table` / `mysql_table_info` | 索引与建表信息 |
| `mysql_table_count` / `mysql_sample_table` | 计数 / 采样 |
| `mysql_list_profiles` | 列出已配置的 profile |

所有工具都接受可选的 `profile` 参数来切换连接。

## 安全模型

| 规则 | 落地位置 |
|---|---|
| 只读强制 | `guard.guard_sql` |
| DDL / 危险语句 | `guard.guard_sql` |
| 多语句 / 注释注入 | `guard.clean_sql` |
| 自动 LIMIT + 上限 | `guard.apply_limit` |
| 写操作必须带 WHERE | `guard.guard_sql` |
| 标识符校验 | `guard.identifier` / `guard.split_table` |
| schema 白名单 | `guard.check_schema_allowed` |

## 测试

```bash
pytest
```

护栏是纯函数，测试不依赖数据库连接。

## 已知边界

- 目前仅支持 MySQL；
- 单进程、每 profile 一个连接，未做连接池；
- 写能力需要显式把 `read_only` 设为 `false`，生产建议保持只读。

## License

MIT
