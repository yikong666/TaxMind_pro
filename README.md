# TaxMind Pro

TaxMind Pro 是面向税务师事务所、代理记账机构和财税咨询机构的内部专业辅助系统。
当前仓库已具备可演示、可评测的 P0 专业辅助原型：受控政策证据检索、确定性风险规则、
办税事项读模型、人工审核、反馈与审计。它仍不接入真实客户资料、电子税务局、自动申报或正式模型生成。

## 安全边界

- 仅使用官方公开资料和虚构、匿名化或经授权的数据。
- 结果只能作为内部分析和客户答复草稿，必须由专业人员审核。
- 风险命中和风险等级由确定性规则决定，LLM 不得改写规则结论。
- MySQL 是结构化事实源；Milvus 和 Neo4j 仅作为可重建投影。

## 环境基线

- Python 3.12，由 `uv` 管理。
- Node.js 24、pnpm 11。
- Windows 本地开发优先使用 `scripts/*.ps1`；CI 使用 Bash/Makefile 等价入口。

### 本地基础设施

复制 `.env.example` 为本地 `.env` 后，可先启动 MySQL、Redis、MinIO、Milvus 与 Neo4j：

```powershell
docker compose up -d
```

迁移只通过 Alembic 执行；首次接入空库前先确认 `.env` 中的 MySQL 参数：

```powershell
Set-Location apps/backend
uv run alembic upgrade head
```

## 当前可运行范围

- 政策检索：仅返回已审核、在业务日期有效的证据；缺少本地证据时明确标记全国口径回退。
- 事项工作台：缺业务日期或地区时停止分析并追问；风险结果仅由确定性规则产生。
- 办税事项、审核、反馈与审计：提供机构范围 API 和虚构预览页面；审计查询不返回敏感快照正文。
- P0 验收：使用虚构金标准验证范围闸门、规则依据、审计脱敏和检索降级；外部依赖未就绪时如实记录为未验证。

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
- [MVP 产品需求与功能规格（PRD）](docs/product/TaxMind-Pro-MVP-PRD.md)
- [本地开发手册](docs/runbooks/local-development.md)
- [P0 演示与验收手册](docs/runbooks/p0-acceptance.md)
- [变更记录](docs/CHANGELOG.md)
