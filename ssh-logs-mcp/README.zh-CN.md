# ssh-logs-mcp

[![CI](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/wangke-112/agent-safe-tools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

一个**只读**的远程日志检索 MCP Server，供 AI Agent（Codex / Claude Code / OpenCode / Cursor 等任何 MCP 宿主）安全地查生产/测试环境的服务日志。

> 很多"日志查询"方案把安全规则写在提示词里，**靠模型自觉**。
> `ssh-logs-mcp` 把**命令白名单、禁止重定向、禁止命令拼接**这些红线**写进代码**，模型越界会被直接拒绝，并且这些规则可单元测试。

[English](./README.md) | [简体中文](./README.zh-CN.md)

> **定位**：本项目核心是 **MCP Server**；`skill/` 是**建议安装**的 Skill 适配层，供支持 Skill 的宿主（Codex / Claude Code）使用。

## 特性

- **命令白名单**：只允许 `tail / head / grep / zgrep / zcat / ls / wc / cat`；
- **禁止危险写法**：`;`、`&&`、`||`、`>`、`<`、反引号、`$()`、`..` 全部拦截；
- **流式命令必须有界**：`cat`/`zcat` 必须被 `head`/`tail` 限制，防止拉爆大日志；
- **grep 加固**：禁止 `--file`、禁止递归 `-r/-R`；`tail` 禁止 `-f` 跟随模式；
- **多环境配置**：`pre` / `test` / `prd` ... 每个环境独立主机与凭证；
- **生产默认禁用**：`forbidden` 标记的环境拒绝连接，需显式开启；
- **中文解码**：UTF-8 → GBK 自动回退，避免乱码；
- **凭证不进仓库**：从用户目录下的配置文件读取，可用 SSH 密钥。

## 安装

未发布到 PyPI，从源码安装：

```bash
git clone https://github.com/wangke-112/agent-safe-tools.git
pip install -e agent-safe-tools/ssh-logs-mcp

# 或已在仓库内：
pip install -e .
```

## 配置

默认读取 `~/.config/ssh-logs-mcp/servers.json`，可用环境变量 `SSH_LOGS_CONFIG` 覆盖。

参考 [`examples/servers.example.json`](./examples/servers.example.json)：

```json
{
  "envs": {
    "test": {
      "desc": "内部测试机",
      "host": "10.0.0.10",
      "port": 22,
      "user": "reader",
      "password": "CHANGE_ME"
    },
    "prd": {
      "desc": "生产-默认禁止",
      "host": "10.0.0.20",
      "port": 22,
      "user": "reader",
      "password": "CHANGE_ME",
      "forbidden": true
    }
  }
}
```

用 SSH 密钥时把 `password` 换成 `key_path`。

## 在各宿主里接入

**Codex（`~/.codex/config.toml`）**

```toml
[mcp_servers.ssh_logs]
type = "stdio"
command = "ssh-logs-mcp"
```

**Claude Code / OpenCode / Cursor（MCP JSON）**

```json
{ "mcpServers": { "ssh_logs": { "command": "ssh-logs-mcp" } } }
```

## 安装 Skill（建议安装）

MCP 提供工具，`skill/` 目录是**建议安装**的 Skill 层，告诉模型什么时候用、怎么用、红线是什么。只装 MCP 时模型仍能调用，但**触发没那么可靠**；装上 Skill 后模型会读工作流与安全规则：

```bash
# Codex
mkdir -p ~/.codex/skills/ssh-logs-mcp
cp -r skill/. ~/.codex/skills/ssh-logs-mcp/

# Claude Code
mkdir -p ~/.claude/skills/ssh-logs-mcp
cp -r skill/. ~/.claude/skills/ssh-logs-mcp/
```

## 暴露的工具

| 工具 | 说明 |
|---|---|
| `list_envs` | 列出已配置环境（含是否禁用） |
| `run_readonly` | 执行一条**经过白名单校验**的只读命令 |
| `tail_log` | 查看文件末尾 N 行 |
| `grep_log` | 在文件里检索（可选忽略大小写、上下文行） |
| `zgrep_log` | 检索 gzip 归档日志 |
| `list_logs` | 列出目录下的日志文件 |

## 安全模型

| 规则 | 落地位置 |
|---|---|
| 命令白名单 | `policy.validate_command` |
| 禁止 `;`/`&&`/`||`/重定向/反引号/`$()` | `policy.validate_command` |
| 禁止路径穿越 `..` | `policy.validate_command` |
| `cat`/`zcat` 必须有界 | `policy.validate_command` |
| `grep --file` / 递归 拦截 | `policy._check_options` |
| `tail -f` 拦截 | `policy._check_options` |
| 生产环境禁用 | `config.get_env` + `forbidden` |

## 测试

```bash
pytest
```

命令策略是纯函数，测试不依赖 SSH 连接。

## 已知边界

- 依赖 `paramiko`，默认使用 `AutoAddPolicy`（不校验 host key），生产建议改造为固定 known_hosts；
- 命令校验基于白名单 + 禁用子串，不是完整的 shell 解析器，但已覆盖常见注入手法；
- 为安全起见，`grep_log` / `zgrep_log` 的 `pattern` 不接受 `|`、`()`、`$` 等复杂正则字符；需要复杂管道时请用 `run_readonly` 自行构造（同样受白名单校验）；
- 只支持基于行的日志命令，不含 `journalctl` 等系统日志源。

## License

MIT
