# Contributing

感谢参与。这个仓库包含两个互相独立的包，改动时请分别验证。

## 开发环境

```bash
# 任选一个子项目
cd safe-mysql-mcp     # 或 cd ssh-logs-mcp
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -e ".[dev]"
```

## 跑测试

```bash
pytest
```

两个子项目都有名为 `test_config.py` 的测试文件，因此**请分别进入子目录运行 pytest**，不要在仓库根目录一次性运行（会因模块同名而收集失败）。

## 提交约定

- 提交信息使用简洁的祈使句，例如 `feat(safe-mysql-mcp): add schema allowlist`；
- 新增安全规则时，请**同时补单元测试**——护栏是纯函数，测试成本很低；
- 不要把任何凭证、主机名、内部地址写入代码、测试、示例或提交信息。

## 安全规则的设计原则

1. **红线在代码里**，不在提示词里；
2. 默认拒绝（allowlist 优先于 blocklist）；
3. 只读为默认，写能力必须显式开启；
4. 凭证永不入库。
