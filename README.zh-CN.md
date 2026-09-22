# agent-safe-tools

[![CI](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

给 AI Agent 用的**安全只读工具集**。面向任何支持 MCP 的宿主（Codex / Claude Code / OpenCode / Cursor 等）。

核心理念：**把安全红线从提示词下沉到代码**——不靠模型自觉，靠校验强制，并有单元测试覆盖。

[English](./README.md) | [简体中文](./README.zh-CN.md)

## 包含的项目

| 项目 | 说明 | 安装 |
|---|---|---|
| [`safe-mysql-mcp`](./safe-mysql-mcp) | 默认只读、带 SQL 护栏的 MySQL MCP Server | `pip install -e ./safe-mysql-mcp` |
| [`ssh-logs-mcp`](./ssh-logs-mcp) | 远程只读日志检索 MCP Server，命令白名单在代码里强制 | `pip install -e ./ssh-logs-mcp` |

两个项目互相独立，也可以各自作为单独仓库发布。

## 快速开始

```bash
git clone https://github.com/wangke-112/agent-safe-tools.git
cd agent-safe-tools

# MySQL（只读）
pip install -e ./safe-mysql-mcp
export MYSQL_HOST=127.0.0.1 MYSQL_USER=readonly_user MYSQL_PASSWORD=****** MYSQL_DATABASE=app
safe-mysql-mcp

# 远程日志（只读）
pip install -e ./ssh-logs-mcp
export SSH_LOGS_CONFIG=~/.config/ssh-logs-mcp/servers.json
ssh-logs-mcp
```

在宿主里的接入配置见各自 README 的「在各宿主里接入」一节。

## 仓库结构

```text
agent-safe-tools/
├── safe-mysql-mcp/
│   ├── src/safe_mysql_mcp/     # guard / config / db / server
│   ├── examples/               # profiles 与 MCP 配置模板
│   └── tests/                  # SQL 护栏单测（纯函数，无需数据库）
├── ssh-logs-mcp/
│   ├── src/ssh_logs_mcp/       # policy / config / transport / server
│   ├── examples/               # servers.json 模板
│   └── tests/                  # 命令策略单测（无需 SSH）
└── .github/workflows/ci.yml    # 多 Python 版本 CI
```

## 为什么是「安全」

让 Agent 直连生产库、跑远程命令很危险。多数现成的 MCP Server 只负责"连上"，安全交给模型遵守提示词。本项目把限制写进代码：

- **只读强制**、DDL / 危险语句拦截、自动补 `LIMIT`、写操作必须有 `WHERE`；
- **命令白名单**、禁止 `;` / `&&` / 重定向 / 反引号 / `$()`、禁止路径穿越；
- **生产环境默认禁用**，需要显式开启；
- **凭证只走环境变量 / 本机配置文件**，永不入库。

这些规则都是**纯函数**，有单元测试覆盖。

## 测试

```bash
# 分别进入子项目运行（两个项目各自独立）
cd safe-mysql-mcp && pip install -e ".[dev]" && pytest
cd ../ssh-logs-mcp && pip install -e ".[dev]" && pytest
```

## License

[MIT](./LICENSE)
