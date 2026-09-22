# Changelog

本项目采用 [Semantic Versioning](https://semver.org/)。

## [0.1.0] - 2026-09-22

### Added

- `safe-mysql-mcp`：默认只读的 MySQL MCP Server
  - 代码级护栏：只读强制、DDL/危险语句拦截、多语句与注释拦截、自动 LIMIT、写操作必须带 WHERE、标识符校验、schema 白名单
  - 多 profile 配置（环境变量或 `profiles.json`）
  - 14 个工具：ping / current_database / query / execute / explain / list_databases / list_tables / list_columns / describe_table / list_indexes / show_create_table / table_info / table_count / sample_table / list_profiles
  - 13 个单元测试
- `ssh-logs-mcp`：远程只读日志检索 MCP Server
  - 代码级命令白名单：禁止 `;` / `&&` / `||` / 重定向 / 反引号 / `$()` / 路径穿越，`cat`/`zcat` 必须有界，禁递归 grep，禁 `tail -f`
  - 多环境配置（`servers.json`），生产环境 `forbidden` 默认禁用
  - UTF-8 / GBK 自适应解码、`altPort` 回退
  - 6 个工具：list_envs / run_readonly / tail_log / grep_log / zgrep_log / list_logs
  - 12 个单元测试
- 每个包附带 `SKILL.md` 与 `agents/openai.yaml`，可作为 Codex / Claude Code 的 Skill 安装
- GitHub Actions CI：Python 3.10 / 3.11 / 3.12 矩阵，分别测试两个子项目
