# TaxMind Pro

TaxMind Pro 是面向税务师事务所、代理记账机构和财税咨询机构的内部专业辅助系统。
当前仓库处于第一批工程基座阶段，只提供可运行的 API/Web 脚手架、统一契约和质量门禁，
尚未实现税务业务判断、知识采集、GraphRAG 或真实模型调用。

## 安全边界

- 仅使用官方公开资料和虚构、匿名化或经授权的数据。
- 结果只能作为内部分析和客户答复草稿，必须由专业人员审核。
- 风险命中和风险等级由确定性规则决定，LLM 不得改写规则结论。
- MySQL 是结构化事实源；Milvus 和 Neo4j 仅作为可重建投影。

## 环境基线

- Python 3.12，由 `uv` 管理。
- Node.js 24、pnpm 11。
- Windows 本地开发优先使用 `scripts/*.ps1`；CI 使用 Bash/Makefile 等价入口。

## 当前可运行范围

```powershell
# 后端依赖与检查
Set-Location apps/backend
uv sync --all-groups
uv run ruff check src tests
uv run mypy src tests
uv run pytest tests -v

# 启动 API
uv run uvicorn taxmind.entrypoints.api.main:create_app --factory --port 8000

# 前端（另开终端，在仓库根目录）
pnpm install
pnpm --filter @taxmind/web dev
```

健康检查：

- `GET /health/live`：进程活性，不访问外部存储。
- `GET /health/ready`：依赖就绪状态；基础设施未接入时会如实返回 `not_ready`。
- `GET /health/version`：应用、构建和契约版本。

## 文档

- [技术开发设计](docs/architecture/TaxMind-Pro-Development-Design.md)
- [系统架构图](docs/architecture/taxmind-pro-system-architecture.html)
- [脚手架与文件契约](docs/development/TaxMind-Pro-Project-Scaffold-Spec.md)
- [本地开发手册](docs/runbooks/local-development.md)
- [变更记录](docs/CHANGELOG.md)

产品 PRD 尚未归档。进入 Identity、Cases、Knowledge、Risk 等业务模块前必须补齐或再次确认范围。