# TaxMind Pro 项目脚手架与文件契约说明书（MVP）

> 文档定位：项目经理／技术负责人交付给 Codex 的仓库初始化与编码边界说明。  
> 上游基线：`TaxMind-Pro-MVP-PRD.md`、`taxmind-pro-system-architecture.html`、`TaxMind-Pro-Development-Design.md`。  
> 文档版本：v1.0-draft。  
> 本轮产物：目录树、目录与文件职责、核心 function 契约、依赖方向、配置文件模板和脚手架验收标准。  
> 本轮不包含：数据库 DDL 全量 migration、业务函数实现、页面视觉细节和正式测试数据。

---

## 0. 结论先行

### 0.1 最终仓库形态

采用 **Monorepo＋模块化单体**：

- 一个后端 Python 工程，包含 FastAPI、Celery Worker、Scheduler 三个进程入口；
- 一个 React Web 工程；
- 一份跨前后端契约目录；
- 一套 Docker Compose 开发基础设施；
- 测试按 unit／integration／contract／golden／security 分层；
- 不拆成多个后端微服务，不建立多个重复的 Python 包。

这样组织的原因是：API、Worker 和 Scheduler 使用同一领域模型、Repository 和配置。如果为了部署进程而拆成三个代码仓库，会产生共享模型复制、版本联动和本地开发成本，MVP 收益不足。

### 0.2 本文固定的工程基线

| 项目 | 决策 | 说明 |
|---|---|---|
| Python | 3.12.x | 主动选择成熟兼容基线；不追随最新 3.14，降低 Milvus／OCR／模型依赖兼容风险 |
| Python 包管理 | uv | 解析快、锁文件明确，开发与 CI 使用同一 `uv.lock` |
| Node.js | 24 LTS | Node 官方当前 LTS 线；不使用 Current 版 Node 26 |
| 前端包管理 | pnpm 11 | pnpm 12 刚发布，不作为首个脚手架基线；锁定 11.x |
| Web | React 19.2＋TypeScript＋Vite 8.1 | SPA 足够，不引入 Next.js／SSR |
| UI | Ant Design＋CSS Modules | 专业工作台组件优先，不叠加第二套 UI 框架 |
| 前端数据 | TanStack Query＋轻量 Zustand | 服务端状态和少量会话状态分离 |
| API | FastAPI＋Pydantic v2 | REST JSON＋SSE |
| ORM／迁移 | SQLAlchemy 2 async＋Alembic | Repository 隔离 ORM，migration 是唯一建表入口 |
| 异步任务 | Celery＋Redis | 采集、解析、嵌入、图同步、评测 |
| 工作流 | LangGraph | 查询运行、追问暂停和恢复 |
| 本地部署 | Docker Compose | 基础设施容器化；前后端支持本机热更新 |

截至 2026-08-29，Node 官方将 v24 标为 LTS，React 官方文档为 19.2，Vite 8.1 已稳定发布，MySQL 8.4 属于 LTS 发行线。版本决策参考 [Node.js Releases](https://nodejs.org/en/about/previous-releases)、[React Versions](https://react.dev/versions)、[Vite 8.1](https://vite.dev/blog/announcing-vite8-1) 和 [MySQL 8.4 LTS](https://dev.mysql.com/doc/refman/8.4/en/mysql-releases.html)。Python 官方已有更新版本，但本文为了模型与数据库驱动兼容性明确固定 3.12，而非无意识使用旧版本。

### 0.3 配置模板使用规则

1. 本文给出的配置是“脚手架基线”，Codex 落盘后必须生成 lockfile，再记录实际解析版本。
2. 容器镜像必须在首次成功联调后改为精确 patch tag 或 digest；禁止正式环境使用 `latest`。
3. `.env.example` 只放变量名和安全示例，不放真实密钥。
4. `uv.lock`、`pnpm-lock.yaml` 必须提交 Git；真实 `.env`、模型缓存、MinIO／MySQL 数据目录不得提交。
5. OpenAPI 和 JSON Schema 是契约，前端类型由契约生成，不手写第二份同名 DTO。

---

## 1. 完整目录树

```text
taxmind-pro/
├── README.md
├── AGENTS.md
├── LICENSE
├── .editorconfig
├── .gitattributes
├── .gitignore
├── .env.example
├── .python-version
├── .nvmrc
├── .pre-commit-config.yaml
├── Makefile
├── package.json
├── pnpm-workspace.yaml
├── pnpm-lock.yaml                         # 安装依赖后生成并提交
├── compose.yaml
├── compose.override.yaml.example
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── apps/
│   ├── backend/
│   │   ├── README.md
│   │   ├── pyproject.toml
│   │   ├── uv.lock                        # uv sync 后生成并提交
│   │   ├── alembic.ini
│   │   ├── src/
│   │   │   └── taxmind/
│   │   │       ├── __init__.py
│   │   │       ├── bootstrap/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── settings.py
│   │   │       │   ├── logging.py
│   │   │       │   ├── container.py
│   │   │       │   └── lifespan.py
│   │   │       ├── entrypoints/
│   │   │       │   ├── api/
│   │   │       │   │   ├── main.py
│   │   │       │   │   ├── router_registry.py
│   │   │       │   │   ├── dependencies.py
│   │   │       │   │   ├── middleware.py
│   │   │       │   │   ├── exception_handlers.py
│   │   │       │   │   └── health.py
│   │   │       │   ├── worker/
│   │   │       │   │   ├── celery_app.py
│   │   │       │   │   ├── task_registry.py
│   │   │       │   │   └── signals.py
│   │   │       │   └── scheduler/
│   │   │       │       └── beat_schedule.py
│   │   │       ├── shared/
│   │   │       │   ├── domain/
│   │   │       │   │   ├── ids.py
│   │   │       │   │   ├── enums.py
│   │   │       │   │   ├── errors.py
│   │   │       │   │   ├── events.py
│   │   │       │   │   └── value_objects.py
│   │   │       │   ├── application/
│   │   │       │   │   ├── clock.py
│   │   │       │   │   ├── pagination.py
│   │   │       │   │   ├── principal.py
│   │   │       │   │   ├── unit_of_work.py
│   │   │       │   │   ├── idempotency.py
│   │   │       │   │   └── transaction.py
│   │   │       │   └── contracts/
│   │   │       │       ├── api.py
│   │   │       │       ├── evidence.py
│   │   │       │       ├── retrieval.py
│   │   │       │       ├── rules.py
│   │   │       │       ├── generation.py
│   │   │       │       └── stream_events.py
│   │   │       ├── modules/
│   │   │       │   ├── identity/
│   │   │       │   │   ├── domain.py
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── repository.py
│   │   │       │   │   ├── service.py
│   │   │       │   │   ├── security.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   └── router.py
│   │   │       │   ├── cases/
│   │   │       │   │   ├── domain.py
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── repository.py
│   │   │       │   │   ├── service.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   └── router.py
│   │   │       │   ├── conversations/
│   │   │       │   │   ├── domain.py
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── repository.py
│   │   │       │   │   ├── memory.py
│   │   │       │   │   ├── service.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   └── router.py
│   │   │       │   ├── sources/
│   │   │       │   │   ├── domain.py
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── repository.py
│   │   │       │   │   ├── collector.py
│   │   │       │   │   ├── service.py
│   │   │       │   │   ├── tasks.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   └── router.py
│   │   │       │   ├── documents/
│   │   │       │   │   ├── domain.py
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── repository.py
│   │   │       │   │   ├── parsers.py
│   │   │       │   │   ├── normalizer.py
│   │   │       │   │   ├── chunker.py
│   │   │       │   │   ├── versioning.py
│   │   │       │   │   ├── service.py
│   │   │       │   │   ├── tasks.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   └── router.py
│   │   │       │   ├── knowledge/
│   │   │       │   │   ├── domain.py
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── repository.py
│   │   │       │   │   ├── extraction.py
│   │   │       │   │   ├── normalization.py
│   │   │       │   │   ├── validation.py
│   │   │       │   │   ├── publishing.py
│   │   │       │   │   ├── impact.py
│   │   │       │   │   ├── service.py
│   │   │       │   │   ├── tasks.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   └── router.py
│   │   │       │   ├── faq/
│   │   │       │   │   ├── domain.py
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── repository.py
│   │   │       │   │   ├── validation.py
│   │   │       │   │   ├── service.py
│   │   │       │   │   ├── tasks.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   └── router.py
│   │   │       │   ├── procedures/
│   │   │       │   │   ├── domain.py
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── repository.py
│   │   │       │   │   ├── validation.py
│   │   │       │   │   ├── service.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   └── router.py
│   │   │       │   ├── risk/
│   │   │       │   │   ├── domain.py
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── repository.py
│   │   │       │   │   ├── dsl.py
│   │   │       │   │   ├── evaluator.py
│   │   │       │   │   ├── validation.py
│   │   │       │   │   ├── service.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   └── router.py
│   │   │       │   ├── retrieval/
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── ports.py
│   │   │       │   │   ├── exact.py
│   │   │       │   │   ├── hybrid.py
│   │   │       │   │   ├── graph.py
│   │   │       │   │   ├── faq.py
│   │   │       │   │   ├── fusion.py
│   │   │       │   │   ├── rerank.py
│   │   │       │   │   └── service.py
│   │   │       │   ├── orchestration/
│   │   │       │   │   ├── state.py
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   ├── router_classifier.py
│   │   │       │   │   ├── fact_gate.py
│   │   │       │   │   ├── planner.py
│   │   │       │   │   ├── graph_builder.py
│   │   │       │   │   ├── service.py
│   │   │       │   │   └── api_router.py
│   │   │       │   ├── generation/
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   ├── prompt_builder.py
│   │   │       │   │   ├── claim_parser.py
│   │   │       │   │   ├── citation_validator.py
│   │   │       │   │   ├── confidence.py
│   │   │       │   │   └── service.py
│   │   │       │   ├── reviews/
│   │   │       │   │   ├── domain.py
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── repository.py
│   │   │       │   │   ├── service.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   └── router.py
│   │   │       │   ├── feedback/
│   │   │       │   │   ├── domain.py
│   │   │       │   │   ├── schemas.py
│   │   │       │   │   ├── repository.py
│   │   │       │   │   ├── service.py
│   │   │       │   │   ├── models.py
│   │   │       │   │   └── router.py
│   │   │       │   └── audit/
│   │   │       │       ├── schemas.py
│   │   │       │       ├── repository.py
│   │   │       │       ├── service.py
│   │   │       │       ├── models.py
│   │   │       │       └── router.py
│   │   │       └── infrastructure/
│   │   │           ├── mysql/
│   │   │           │   ├── base.py
│   │   │           │   ├── session.py
│   │   │           │   ├── uow.py
│   │   │           │   └── outbox.py
│   │   │           ├── redis/
│   │   │           │   ├── client.py
│   │   │           │   ├── keyspace.py
│   │   │           │   ├── cache.py
│   │   │           │   └── checkpoint.py
│   │   │           ├── milvus/
│   │   │           │   ├── client.py
│   │   │           │   ├── collections.py
│   │   │           │   └── search.py
│   │   │           ├── neo4j/
│   │   │           │   ├── client.py
│   │   │           │   ├── templates.py
│   │   │           │   └── graph_store.py
│   │   │           ├── minio/
│   │   │           │   ├── client.py
│   │   │           │   └── object_store.py
│   │   │           ├── models/
│   │   │           │   ├── gateway.py
│   │   │           │   ├── dashscope_llm.py
│   │   │           │   ├── bge_embedder.py
│   │   │           │   └── bge_reranker.py
│   │   │           ├── http/
│   │   │           │   ├── client.py
│   │   │           │   └── official_source.py
│   │   │           ├── security/
│   │   │           │   ├── tokens.py
│   │   │           │   ├── passwords.py
│   │   │           │   └── redaction.py
│   │   │           └── telemetry/
│   │   │               ├── metrics.py
│   │   │               └── tracing.py
│   │   ├── migrations/
│   │   │   ├── env.py
│   │   │   ├── script.py.mako
│   │   │   └── versions/
│   │   │       └── .gitkeep
│   │   └── tests/
│   │       ├── conftest.py
│   │       ├── factories/
│   │       ├── unit/
│   │       ├── integration/
│   │       ├── contract/
│   │       ├── golden/
│   │       └── security/
│   │
│   └── web/
│       ├── README.md
│       ├── package.json
│       ├── tsconfig.json
│       ├── tsconfig.app.json
│       ├── vite.config.ts
│       ├── eslint.config.js
│       ├── index.html
│       ├── public/
│       └── src/
│           ├── main.tsx
│           ├── vite-env.d.ts
│           ├── app/
│           │   ├── App.tsx
│           │   ├── router.tsx
│           │   ├── providers.tsx
│           │   ├── permissions.ts
│           │   └── error-boundary.tsx
│           ├── api/
│           │   ├── client.ts
│           │   ├── errors.ts
│           │   ├── sse.ts
│           │   └── generated/             # OpenAPI 生成，禁止手改
│           ├── components/
│           │   ├── layout/
│           │   ├── evidence/
│           │   ├── status/
│           │   ├── markdown/
│           │   └── feedback/
│           ├── features/
│           │   ├── auth/
│           │   ├── cases/
│           │   ├── conversation/
│           │   ├── policies/
│           │   ├── faq/
│           │   ├── risk/
│           │   ├── procedures/
│           │   ├── reviews/
│           │   ├── knowledge/
│           │   └── audit/
│           ├── pages/
│           │   ├── LoginPage.tsx
│           │   ├── CaseListPage.tsx
│           │   ├── CaseWorkspacePage.tsx
│           │   ├── PolicySearchPage.tsx
│           │   ├── PolicyDetailPage.tsx
│           │   ├── FaqPage.tsx
│           │   ├── ProcedurePage.tsx
│           │   ├── ReviewQueuePage.tsx
│           │   ├── ReviewDetailPage.tsx
│           │   ├── KnowledgeOpsPage.tsx
│           │   ├── AuditPage.tsx
│           │   └── NotFoundPage.tsx
│           ├── stores/
│           │   ├── auth-store.ts
│           │   └── run-store.ts
│           ├── hooks/
│           │   ├── use-permission.ts
│           │   └── use-run-stream.ts
│           ├── types/
│           │   └── ui.ts
│           ├── test/
│           │   └── setup.ts
│           └── styles/
│               ├── tokens.css
│               └── global.css
│
├── packages/
│   └── contracts/
│       ├── README.md
│       ├── openapi/
│       │   └── taxmind-v1.openapi.json      # 后端导出生成
│       ├── json-schema/
│       │   ├── run-event.schema.json
│       │   ├── risk-rule.schema.json
│       │   ├── generation-output.schema.json
│       │   └── evidence-bundle.schema.json
│       └── examples/
│           ├── create-case.request.json
│           ├── submit-query.request.json
│           ├── facts-required.event.json
│           └── run-completed.event.json
│
├── infra/
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   └── web.Dockerfile
│   ├── neo4j/
│   │   └── constraints.cypher
│   ├── milvus/
│   │   └── README.md
│   └── observability/
│       └── README.md
│
├── scripts/
│   ├── bootstrap.sh
│   ├── wait-for-services.sh
│   ├── export-openapi.sh
│   ├── generate-web-client.sh
│   ├── verify-projections.sh
│   └── seed-demo-data.sh
│
├── tests/
│   ├── contract/
│   ├── e2e/
│   ├── golden/
│   │   ├── questions.jsonl
│   │   ├── expected-evidence.jsonl
│   │   └── README.md
│   └── fixtures/
│       ├── official-documents/
│       └── synthetic-cases/
│
└── docs/
    ├── product/
    │   └── TaxMind-Pro-MVP-PRD.md
    ├── architecture/
    │   ├── taxmind-pro-system-architecture.html
    │   └── TaxMind-Pro-Development-Design.md
    ├── development/
    │   └── TaxMind-Pro-Project-Scaffold-Spec.md
    ├── adr/
    │   ├── 0001-modular-monolith.md
    │   ├── 0002-storage-authority.md
    │   ├── 0003-sse-over-websocket.md
    │   └── 0004-outbox-projections.md
    └── runbooks/
        ├── local-development.md
        ├── knowledge-publish.md
        └── projection-rebuild.md
```

为避免目录树失去可读性，除 `__init__.py` 已有特殊职责的目录外，其余 Python package 的空 `__init__.py` 在树中省略；Codex 落盘时必须补齐。`apps/web/src/api/generated/.gitkeep` 也应创建以保留空目录。

---

## 2. 顶层目录与依赖方向

### 2.1 顶层目录职责

| 目录 | 职责 | 可依赖 | 禁止 |
|---|---|---|---|
| `apps/backend` | 后端业务、API、Worker、Scheduler | `packages/contracts` 的 schema 概念；外部依赖 | 依赖前端源码 |
| `apps/web` | 浏览器应用 | OpenAPI 生成类型、公共 JSON Schema | 直接访问数据库或读取 `.env` 服务端密钥 |
| `packages/contracts` | API／SSE／规则／EvidenceBundle 的版本化契约 | 无运行时代码 | 手工维护一份与后端不同的 DTO 真相 |
| `infra` | 本地容器、镜像和数据库初始化外壳 | 应用构建产物 | 存放业务规则 |
| `scripts` | 可重复的开发／生成／校验命令 | CLI 和配置 | 包含真实密钥、绕过审核直接写正式知识 |
| `tests` | 跨应用 contract、E2E、golden 和固定数据 | 公开 API／测试入口 | 依赖生产真实客户数据 |
| `docs` | 产品、架构、ADR、运行手册 | 无 | 变成实现代码替代品 |

### 2.2 后端依赖规则

依赖方向固定为：

`entrypoints → modules.application/service → domain/contracts → shared abstractions`

`infrastructure → shared ports/contracts`，由 `bootstrap/container.py` 注入到 service。

具体限制：

1. `domain.py` 不得 import FastAPI、SQLAlchemy、Redis、Milvus、Neo4j、DashScope。
2. `service.py` 可依赖 Repository Protocol、UnitOfWork、Clock、ModelGateway 等接口，不直接创建 SDK client。
3. `repository.py` 同时声明 Protocol 和 MySQL 实现时，Service 只类型依赖 Protocol；后续规模增大可再拆 `ports.py`／`repository_mysql.py`。
4. `router.py` 只负责 HTTP schema、权限依赖、调用 Service 和映射响应，不包含 SQL、规则表达式和提示词。
5. `tasks.py` 只将 Celery payload 转换为应用命令；可重试规则在任务包装层，业务幂等在 Service／Repository。
6. 模块间不能 import 对方 ORM `models.py`。跨模块只通过公开 Service／Contract 或 ID 关联。

### 2.3 前端依赖规则

1. `pages` 负责页面编排，依赖 `features` 和共享 `components`。
2. `features` 负责用例状态、查询 hooks 和局部 UI，不互相直接读取内部 store。
3. `api/generated` 由 OpenAPI 生成且禁止手改；`api/client.ts` 统一认证、request ID 和错误映射。
4. 只有 `api/sse.ts` 处理 SSE 字节流；组件不直接解析 `text/event-stream`。
5. 服务端状态放 TanStack Query；仅认证信息、当前 run 的瞬时 UI 状态放 Zustand。

---

## 3. 顶层文件职责

| 文件 | 功能 | 关键约束 |
|---|---|---|
| `README.md` | 项目介绍、5 分钟启动、常用命令、文档入口 | 不复制整份架构文档 |
| `AGENTS.md` | 给 Codex 的仓库级开发规则 | 必须写明模块边界、测试命令、禁止双写、禁止生成文号 |
| `.env.example` | 开发变量清单 | 无真实 secret；变量与 `Settings` 一一对应 |
| `.python-version` | 固定本地 Python | `3.12` |
| `.nvmrc` | 固定 Node 主版本 | `24` |
| `package.json` | 根 workspace 命令和 packageManager | 不放后端 Python 依赖 |
| `pnpm-workspace.yaml` | pnpm workspace 范围 | 只包含 `apps/web` 和未来 TS packages |
| `Makefile` | 统一开发入口 | 只调用可复现命令，不隐藏不可逆操作 |
| `compose.yaml` | 本地基础设施和可选 app profile | 使用 healthcheck、volume、显式 network |
| `compose.override.yaml.example` | 开发者端口／挂载覆盖示例 | 真正 override 文件不提交 |
| `.pre-commit-config.yaml` | Ruff、格式和基础文件检查 | 不在 hook 里运行耗时 golden test |

---

## 4. 后端公共文件与 Function 契约

### 4.1 `bootstrap` 与 API 入口

| 文件 | Function | 入参 | 出参 | 依赖／异常 |
|---|---|---|---|---|
| `settings.py` | `get_settings()` | 无；读取环境 | 缓存的 `Settings` | Pydantic Settings；缺关键变量抛启动配置错误 |
| `settings.py` | `validate_runtime_settings(settings)` | `Settings` | `None` | 校验生产密钥、CORS、模型和存储 URI；不发网络请求 |
| `logging.py` | `configure_logging(settings)` | Settings | `None` | structlog／标准 logging；初始化失败阻止启动 |
| `container.py` | `build_container(settings)` | Settings | `AppContainer` | 创建 client factory、Repository factory、Services；不得连接网络 |
| `container.py` | `wire_services(container)` | AppContainer | `ServiceRegistry` | 显式依赖注入；禁止全局 Service Locator |
| `lifespan.py` | `app_lifespan(app)` | FastAPI | async context manager | 启动时连接／探活，关闭时释放 pool；任一权威存储失败按策略阻止启动 |
| `api/main.py` | `create_app(settings=None)` | 可选 Settings | FastAPI | 注册中间件、异常处理、路由、lifespan；便于测试注入 |
| `router_registry.py` | `register_routers(app, registry)` | FastAPI、ServiceRegistry | `None` | 统一 `/api/v1` 前缀，禁止模块自行改版本 |
| `dependencies.py` | `get_principal(request)` | Request | `Principal` | 校验 Bearer token；401／403 |
| `dependencies.py` | `require_permissions(*codes)` | 权限代码 | FastAPI dependency | 同时校验租户与权限；禁止仅靠前端隐藏 |
| `middleware.py` | `request_context_middleware(request, call_next)` | Request、next | Response | 创建／透传 request_id、计时、日志上下文 |
| `exception_handlers.py` | `register_exception_handlers(app)` | FastAPI | `None` | DomainError→统一 ErrorEnvelope；隐藏内部堆栈 |
| `health.py` | `liveness()` | 无 | `HealthResponse` | 只验证进程活性，不查外部存储 |
| `health.py` | `readiness(container)` | 容器 | `ReadinessResponse` | 并行探测 MySQL、Redis、必要检索服务；带超时 |

`AppContainer` 只保存 factory／client／service 引用，不保存请求级 `Principal`、DB Session 或事务。请求级对象由 dependency／UnitOfWork 创建。

### 4.2 Shared Domain

| 文件 | 公开对象／Function | 契约 |
|---|---|---|
| `ids.py` | `new_id() -> str` | 生成 UUIDv7 字符串；不可由数据库自增替代 |
| `ids.py` | `parse_id(value: str) -> str` | 校验 UUID 格式并返回规范字符串；非法抛 `ValidationError` |
| `enums.py` | 状态与 route 枚举 | 与开发设计文档一致；数据库存字符串值 |
| `errors.py` | `DomainError(code, message, details, retryable)` | 所有可预期业务异常基类，不带 HTTP 类型 |
| `events.py` | `DomainEvent`、`OutboxEvent` | 必含 event_id、event_type、aggregate、occurred_at、dedupe_key、schema_version |
| `value_objects.py` | `DateRange.contains(date)` | 空 start／end 按无界区间；时区与日期语义明确 |
| `value_objects.py` | `RegionScope.matches(region)` | CN 可覆盖全国政策，地方口径不得反向覆盖其他地区 |
| `value_objects.py` | `Money` | Decimal＋currency；禁止 float |

### 4.3 Shared Application

| 文件 | Function／Protocol | 入参 | 出参／语义 |
|---|---|---|---|
| `clock.py` | `Clock.now()` | 无 | UTC aware datetime；测试注入 FixedClock |
| `pagination.py` | `encode_cursor(payload)`／`decode_cursor(cursor)` | 排序键对象／字符串 | 签名 cursor；非法返回 ValidationError |
| `principal.py` | `Principal.can(permission)` | 权限码 | bool；不查询数据库 |
| `unit_of_work.py` | `UnitOfWork.__aenter__()` | 无 | 请求／任务事务作用域 |
| `unit_of_work.py` | `commit()`／`rollback()` | 无 | 业务记录与 Outbox 同一 MySQL 事务 |
| `idempotency.py` | `execute_once(key, operation)` | org、key、回调 | 已完成则返回原结果；处理中返回冲突；失败允许策略性重试 |
| `transaction.py` | `transactional(handler)` | 应用 handler | 保证异常回滚；不吞 DomainError |

### 4.4 Shared Contracts

| 文件 | 核心类型 | 必填字段 |
|---|---|---|
| `api.py` | `ApiEnvelope[T]`、`ErrorEnvelope`、`Page[T]` | data／error、request_id、cursor |
| `evidence.py` | `EvidenceRef`、`EvidencePath`、`EvidenceBundle` | chunk_id、doc/version、source level、日期、地区、状态、路径和命中原因 |
| `retrieval.py` | `RetrievalPlan`、`Candidate`、`FusedResult` | route、filters、retrievers、rank／score、selected／rejection reason |
| `rules.py` | `RuleExpression`、`RuleResult` | rule version、truth value、facts、missing facts、evidence IDs |
| `generation.py` | `GenerationInput`、`DraftOutput`、`Claim` | 已确认事实、证据、规则、claims、uncertainties、disclaimer |
| `stream_events.py` | SSE event discriminated union | event_id、event_type、run_id、occurred_at、schema_version、payload |

---

## 5. 后端业务模块逐文件契约

### 5.1 通用模块文件模式

| 文件名 | 统一职责 | 允许依赖 | 不允许 |
|---|---|---|---|
| `domain.py` | Entity、Value Object、状态迁移纯函数 | shared domain | ORM、HTTP、SDK |
| `schemas.py` | API／应用 Command、Query、Result 的 Pydantic 模型 | shared contracts | SQLAlchemy model 直接作为响应 |
| `repository.py` | Repository Protocol＋MySQL 实现 | SQLAlchemy、UoW | 生成答案、执行业务工作流 |
| `service.py` | 用例编排、权限后的业务规则、事务边界 | Repository Protocol、shared ports | 创建全局 client、读取环境变量 |
| `models.py` | SQLAlchemy ORM 与索引元信息 | infrastructure mysql base | 被其他业务模块直接 import |
| `router.py` | HTTP method／path／schema／permission | Service | SQL、提示词、SDK |
| `tasks.py` | Celery task adapter、重试、payload 版本 | Service | 复制业务逻辑 |

以下只列每个文件对外的关键函数；私有辅助函数由实现测试驱动，不作为跨模块契约。

### 5.2 Identity & Tenant

| 文件／Function | 入参 | 出参 | 依赖 | 关键异常／副作用 |
|---|---|---|---|---|
| `domain.py::change_member_role(member, role, actor)` | Member、Role、Principal | 新 Member 状态 | 无 | 无权限／最后一个管理员不可移除 |
| `security.py::authenticate(command)` | email、password、org_hint | `AuthResult(user, organizations, access_token, refresh_session)` | UserRepo、PasswordHasher、TokenService、Clock、Audit | 凭据错误统一 AUTH_FAILED；成功／失败写安全审计 |
| `security.py::refresh_session(command)` | refresh token、device context | 新 token pair | AuthSessionRepo、TokenService、Clock | token 轮换，旧 token 立即撤销；复用检测撤销整条 session chain |
| `service.py::invite_member(command, principal)` | org、email、role | `MemberView` | UserRepo、MemberRepo、UoW、Audit | `org_admin`；同机构重复成员冲突 |
| `service.py::update_member(command, principal)` | member_id、role／status、version_no | `MemberView` | MemberRepo、UoW、Audit | 乐观锁；职责分离校验 |
| `repository.py::get_user_by_email(email)` | 规范 email | User／None | AsyncSession | 查询必须使用规范化值 |
| `repository.py::get_member(org_id, user_id)` | 租户＋用户 | Member／None | AsyncSession | 任何成员查询必须带 org_id |

`schemas.py` 包含 `LoginRequest`、`TokenResponse`、`MemberCreate`、`MemberUpdate`、`PrincipalResponse`。`models.py` 映射 `organizations`、`users`、`organization_members`、`auth_sessions`。

### 5.3 Cases

| 文件／Function | 入参 | 出参 | 依赖 | 关键规则 |
|---|---|---|---|---|
| `domain.py::transition_case(case, target)` | Case、CaseStatus | 新状态／DomainError | 无 | 只允许既定状态图；审核通过后画像变化必须回到待审核 |
| `service.py::create_case(command, principal)` | title、region、initial profile | `CaseDetail` | CaseRepo、UoW、Clock、ID、Audit | 创建 case＋profile v1 同事务；数据分类必须 synthetic／anonymized |
| `service.py::get_case(case_id, principal)` | case_id | `CaseDetail` | CaseRepo | Repository 强制 org_id；无权统一 404 |
| `service.py::create_profile_version(command, principal)` | case_id、完整画像、supersedes_version | `SubjectProfileView` | CaseRepo、UoW、Impact marker | 新版本不可变；不能 PATCH 已确认旧版本 |
| `service.py::confirm_facts(command, principal)` | case_id、profile_version、fact decisions | `FactConfirmationResult(new_profile_version, facts)` | CaseRepo、UoW、Audit | proposed→confirmed／rejected；确认事实变化使相关旧草稿审核失效 |
| `service.py::list_case_history(query, principal)` | case_id、cursor | `Page[CaseHistoryItem]` | CaseRepo | 按 occurred_at＋id 稳定排序 |
| `repository.py::lock_case(case_id, org_id)` | ID＋租户 | Case | AsyncSession | 更新画像／状态时 `SELECT ... FOR UPDATE` |

`schemas.py` 包含 `CreateCaseRequest`、`CreateProfileRequest`、`ConfirmFactsRequest`、`CaseDetailResponse`。`models.py` 映射 `consultation_cases`、`case_subject_profiles`、`case_facts`。

### 5.4 Conversations & Memory

| 文件／Function | 入参 | 出参 | 依赖 | 关键规则 |
|---|---|---|---|---|
| `service.py::create_conversation(command, principal)` | case_id、title | Conversation | Case access、ConversationRepo、UoW | 只能在可访问事项内创建 |
| `service.py::append_user_message(command, principal)` | conversation_id、text、idempotency_key | Message | ConversationRepo、Redactor、UoW | 先写 MySQL，再更新 Redis；禁止空文本和超限内容 |
| `service.py::append_assistant_message(command)` | run_id、validated content | Message | ConversationRepo、UoW | 只能保存用户可见结果，不保存隐藏推理 |
| `memory.py::build_context(query)` | org、case、conversation、token_budget | `ConversationContext` | CaseRepo、ConversationRepo、RedisMemory、Tokenizer | 顺序：确认事实→摘要→最近消息；不得让摘要覆盖确认事实 |
| `memory.py::summarize_if_needed(command)` | conversation、covered range | `Summary | None` | ModelGateway、ConversationRepo | 超消息／token 阈值才执行；摘要记录覆盖区间和模型版本 |
| `memory.py::restore_short_memory(conversation_id)` | conversation_id＋tenant | `ShortMemoryState` | MySQL repos、Redis | Redis 丢失后重建，不声称恢复已丢失的流式 delta |
| `repository.py::next_sequence(conversation_id)` | conversation_id | int | 行锁／原子序列 | 同一会话 sequence 唯一且单调递增 |

`schemas.py` 包含 `CreateConversationRequest`、`MessageResponse`、`ConversationContext`。`models.py` 映射 `conversations`、`messages`、`conversation_summaries`。

### 5.5 Sources

| 文件／Function | 入参 | 出参 | 依赖 | 关键规则 |
|---|---|---|---|---|
| `collector.py::fetch_public_resource(request)` | 白名单 URL、条件请求头、最大大小 | `FetchedResource(status, headers, bytes_ref, hash)` | OfficialHttpClient、ObjectStore | 只允许白名单域名和公开 URL；不处理验证码／登录绕过 |
| `collector.py::discover_links(page, rules)` | HTML、白名单规则 | `list[DiscoveredLink]` | HTML parser | 规范 URL、去追踪参数、限制同域和层级 |
| `service.py::create_ingestion_job(command, principal)` | source_site、job_type、URL／object key | `IngestionJobView` | SourceRepo、UoW、Outbox | knowledge_admin；dedupe_key 防重复 |
| `service.py::execute_ingestion_job(job_id)` | job_id | `IngestionOutcome` | Collector、ObjectStore、SourceRepo、DocumentService | 幂等；只记录安全错误；下载原件先写 MinIO |
| `tasks.py::run_ingestion_job(payload_v1)` | job_id、schema_version | Celery result summary | SourceService | 网络／429／5xx 可重试；权限／schema 错误不重试 |
| `repository.py::claim_job(job_id, worker_id)` | IDs | bool | MySQL 原子更新 | 只有 queued／retryable 可 claim |

`models.py` 映射 `source_sites`、`ingestion_jobs`；原始正文不进此模块表。

### 5.6 Documents

| 文件／Function | 入参 | 出参 | 依赖 | 关键规则 |
|---|---|---|---|---|
| `parsers.py::select_parser(mime_type, filename)` | MIME、文件名 | `DocumentParser` | Parser registry | 不可信扩展名不能覆盖 MIME 检测 |
| `DocumentParser.parse(object_ref)` | MinIO ref | `ParsedDocument` | ObjectStore／OCR adapter | 产出结构节点、文本、表格、警告；不发布知识 |
| `normalizer.py::normalize_document(parsed)` | ParsedDocument | `NormalizedDocument` | 受控清洗规则 | 保留条号、表格和标题层级；记录 normalizer_version |
| `chunker.py::chunk_document(document, policy)` | 规范文档、ChunkPolicy | `ChunkingResult` | Tokenizer | 结构优先；子块 300—600 tokens；不切断法条条件列表 |
| `versioning.py::build_canonical_key(metadata)` | 文号、机构、URL 等 | canonical_key | URL／文号规范化器 | 文号优先；无文号才使用规范 URL 哈希 |
| `versioning.py::detect_version(existing, fetched_hash)` | 已有版本、hash | `unchanged | new_version` | 无 | hash 未变不建新版本 |
| `versioning.py::diff_chunks(old, new)` | 两版本 chunks | `DocumentDiff` | hash／sequence matcher | 输出 added／modified／removed 和影响 ID |
| `service.py::process_document(command)` | ingestion_job、raw object | `ProcessDocumentResult` | Parser、Normalizer、Chunker、DocumentRepo、UoW、Outbox | 文档、版本、chunks 同事务入主库；向量／图通过 Outbox |
| `tasks.py::parse_document(payload_v1)` | job_id、document_version_id | task summary | DocumentService | OCR 使用独立 queue／限流 |

`schemas.py` 提供文档后台查询 DTO；`models.py` 映射 `source_documents`、`document_versions`、`document_chunks`、`document_relations`。

### 5.7 Knowledge Governance

| 文件／Function | 入参 | 出参 | 依赖 | 关键规则 |
|---|---|---|---|---|
| `extraction.py::extract_candidates(command)` | document_version、chunks | `ExtractionBatch` | Regex extractors、ModelGateway、PromptVersion | 规则先行；LLM 只产 schema 化候选和原文 span |
| `normalization.py::normalize_candidate(candidate)` | 候选实体／关系 | `NormalizedCandidate` | ControlledTermRepo | 无法唯一消歧标 ambiguous，不能自动发布 |
| `validation.py::validate_relation(candidate)` | 两端对象、关系、来源 | `ValidationReport` | KnowledgeRepo、Date rules | source_chunk 必填；谓词白名单；日期合法；沿革环检查 |
| `publishing.py::create_publish_batch(command)` | 选中候选和版本 | `PublishBatch` | KnowledgeRepo、UoW | 建不可变 manifest，不直接激活 |
| `publishing.py::validate_publish_batch(batch_id)` | batch_id | `PublishValidationReport` | FAQ／Risk／Procedure validators、Projection ports | schema、证据、测试、租户、checksum 全检 |
| `publishing.py::activate_snapshot(command)` | batch、expected active snapshot | `KnowledgeSnapshotView` | UoW、Outbox、ProjectionStatusRepo | 乐观切换；投影 smoke test 成功才 active |
| `impact.py::analyze_document_update(command)` | old/new document version | `ImpactReport` | KnowledgeRepo、FAQRepo、RiskRepo、AnswerRepo | 反查 FAQ、规则、流程、主张；不改历史答案 |
| `tasks.py::sync_projection(payload_v1)` | event_id、projection_type | task summary | Milvus／Neo4j adapter、ProjectionRepo | 幂等 upsert；checksum 不一致进入 dead／告警 |

`models.py` 映射 `controlled_terms`、`knowledge_objects`、`knowledge_object_versions`、`knowledge_relations`、`condition_sets`、`knowledge_snapshots`、`knowledge_snapshot_items`、`knowledge_publish_batches`、`outbox_events`、`projection_sync_states`。

### 5.8 FAQ

| 文件／Function | 入参 | 出参 | 依赖 | 关键规则 |
|---|---|---|---|---|
| `service.py::create_faq(command, principal)` | type、question、answer、scope、evidences | FAQ v1 draft | FAQRepo、EvidenceRepo、UoW | institution FAQ 强制 org_id；official 需 source document |
| `service.py::create_faq_version(command, principal)` | faq_id、base_version、变更内容 | 新 immutable version | FAQRepo、UoW | 已发布版本不可 PATCH |
| `validation.py::validate_faq_version(version_id)` | version_id | `FaqValidationReport` | DocumentRepo、Policy status service | 至少一 primary；日期、地区、主体和证据状态一致 |
| `service.py::publish_faq(command, principal)` | version、review_task、evidence_hash | Published FAQ | ReviewService、FAQRepo、UoW、Outbox | 自审限制；证据变化返回版本冲突 |
| `service.py::retire_faq(command, principal)` | faq_id、reason、version | Retired FAQ | FAQRepo、UoW、Outbox、Audit | 先主库停用，后删除投影 |
| `service.py::promote_case_memory(command, principal)` | approved case、范围、脱敏摘要 | memory draft | CaseRepo、ReviewRepo、Redactor、FAQRepo | 不直接发布；普通对话不能调用 |
| `tasks.py::index_faq(payload_v1)` | faq_version、embedding_version | projection result | Embedder、Milvus、ProjectionRepo | 只处理 published／available |

`models.py` 映射 `faqs`、`faq_versions`、`faq_variants`、`faq_evidence_links`、`approved_case_memories`。

### 5.9 Procedures

| 文件／Function | 入参 | 出参 | 依赖 | 关键规则 |
|---|---|---|---|---|
| `service.py::search_procedures(query, principal)` | q、region、date、subject、tax | `Page[ProcedureCard]` | ProcedureRepo、PolicyStatus | 地区和日期硬过滤；全国资料需标 national_only |
| `service.py::get_procedure(id, context)` | procedure_id、business context | `ProcedureDetail` | ProcedureRepo、EvidenceRepo | 条件材料按三值规则显示 required／not_required／unknown |
| `validation.py::validate_procedure_version(id)` | version_id | report | EvidenceRepo、Rule DSL validator | 每步骤／关键材料有来源；地区和有效期齐全 |
| `service.py::publish_procedure(command, principal)` | version、review task | Published version | Review、UoW、Outbox | 只有 8—12 个首批事项进入 P0 发布 |

`models.py` 映射 `tax_procedures`、`tax_procedure_versions`、`procedure_steps`、`procedure_materials`、`procedure_evidence_links`。

### 5.10 Risk

| 文件／Function | 入参 | 出参 | 依赖 | 关键规则 |
|---|---|---|---|---|
| `dsl.py::parse_expression(raw_json)` | JSON object | `RuleExpression` | JSON Schema／operator registry | 只允许 all／any／not 和白名单叶子操作符；禁止脚本／SQL |
| `validation.py::validate_rule_version(version)` | rule version | `RuleValidationReport` | Fact dictionary、EvidenceRepo | fact_key、类型、日期、证据、checksum、测试齐全 |
| `evaluator.py::evaluate(expression, facts)` | RuleExpression、FactMap | `TruthValue + trace` | Decimal／date evaluator | 三值逻辑；unknown 不能强转 false |
| `service.py::execute_rules(command)` | case/profile version、rule snapshot、scope | `list[RiskFinding]` | RiskRepo、Evaluator、EvidenceRepo、UoW | 先 scope 后 trigger；保存 rule_version 和触发事实 |
| `service.py::run_rule_tests(rule_version_id)` | version ID | `RuleTestReport` | RiskRepo、Evaluator | 发布门禁要求固定用例 100% |
| `service.py::publish_rule(command, principal)` | version、review task | Published Rule | Review、UoW、Outbox | LLM 不参与命中和等级修改 |

`models.py` 映射 `risk_rules`、`risk_rule_versions`、`risk_rule_evidences`、`risk_rule_test_cases`、`risk_findings`。

### 5.11 Retrieval

`retrieval` 不拥有业务主表和 ORM model。它消费标准 `RetrievalPlan`，返回标准候选与 EvidenceBundle。

| 文件／Function | 入参 | 出参 | 依赖 | 契约 |
|---|---|---|---|---|
| `ports.py::ExactRetriever.search(plan)` | plan | `list[Candidate]` | Protocol | 精确文号／结构化元数据 |
| `ports.py::VectorRetriever.search(plan)` | plan | candidates | Protocol | 稠密／BM25 可分通道返回排名 |
| `ports.py::GraphRetriever.expand(anchors, plan)` | anchors＋plan | `list[EvidencePath]` | Protocol | 只返回白名单关系、受限深度路径 |
| `exact.py::retrieve_exact(plan)` | plan | candidates | Document／Procedure repos | 强制 snapshot、date、region、review filters |
| `hybrid.py::retrieve_hybrid(plan)` | plan | dense＋sparse candidates | Milvus adapter | 默认各 Top30；返回原 rank／score，不在此生成答案 |
| `graph.py::expand_graph(plan, anchors)` | plan、文件／实体锚点 | paths＋new candidates | Neo4j adapter、DocumentRepo | 默认深度 2、沿革最大 4；去环和超时 |
| `faq.py::retrieve_faq(plan)` | org context、query、filters | FAQ candidates | Milvus＋FAQRepo | GLOBAL 或 current org；回查证据状态 |
| `fusion.py::weighted_rrf(result_sets, weights, k=60)` | 多通道排名 | fused list | 纯函数 | 相同 candidate ID 合并；保留通道解释 |
| `rerank.py::rerank(query, candidates, limit)` | query、前 30—40 | reranked candidates | Reranker gateway | 模型失败返回 RRF 并标 degraded |
| `fusion.py::build_evidence_bundle(candidates, paths, context)` | rerank 后候选、路径 | EvidenceBundle | DocumentRepo、Conflict detector | 父块回填、去重、8—12 条、每条可定位 |
| `service.py::execute_plan(plan)` | RetrievalPlan | `RetrievalOutcome` | 上述 retrievers | 并行、独立超时、显式降级列表 |

### 5.12 Orchestration

| 文件／Function | 入参 | 出参 | 依赖 | 契约 |
|---|---|---|---|---|
| `state.py::RunState` | — | LangGraph state model | shared contracts | 大正文不进 state，只保存 ID 和必要短文本 |
| `router_classifier.py::classify(query, facts)` | 问题＋确认事实 | `RouteDecision[]` | 确定性规则＋ModelGateway | 多标签；冲突时优先适用性／风险／版本安全路由 |
| `fact_gate.py::required_facts(routes, facts)` | routes＋facts | `FactGateResult` | route fact registry | 日期、地区、主体等按优先级；缺 P0 则 interrupt |
| `planner.py::build_plan(route, context)` | route、facts、snapshot | RetrievalPlan | plan templates | 客户端不能传原始 Milvus filter／Cypher |
| `graph_builder.py::build_analysis_graph(services)` | 依赖集合 | CompiledStateGraph | LangGraph | 固定节点：scope→memory→facts→route→retrieve→rules→generate→validate→persist |
| `service.py::submit_query(command, principal)` | case、conversation、question、profile version、idempotency | `RunAccepted` | Case／Conversation、UoW、Graph executor、Event stream | 先存消息与 run；返回 202；不得同步等待完整答案 |
| `service.py::resume_run(command, principal)` | run、checkpoint version、confirmed facts | `RunAccepted` | Checkpointer、CaseService、Graph executor | checkpoint 乐观锁；事实先持久化再恢复 |
| `service.py::cancel_run(run_id, principal)` | run | RunStatus | RunRepo、Celery control | 尽力取消；不删除已产生结果／审计 |
| `api_router.py::stream_run_events(run_id, last_event_id)` | Bearer principal、run | SSE stream | Redis event store、RunRepo | token 不放 URL；只流用户可见事件 |

`schemas.py` 包含 `SubmitQueryRequest`、`ResumeRunRequest`、`RunStatusResponse`。`orchestration/models.py` 固定映射 `analysis_runs`、`run_routes`、`retrieval_results`，避免把运行记录放入无关模块。

### 5.13 Generation & Validation

| 文件／Function | 入参 | 出参 | 依赖 | 契约 |
|---|---|---|---|---|
| `prompt_builder.py::build_generation_input(context)` | facts、routes、EvidenceBundle、RuleResults、prompt version | `GenerationInput` | PromptRepo | 文档内容标 untrusted；不包含数据库工具和隐藏规则 |
| `service.py::generate_draft(command)` | GenerationInput、model profile | DraftOutput | ModelGateway、schema validator | JSON Schema 失败最多修复一次；失败返回证据／规则而非半截结论 |
| `claim_parser.py::extract_claims(draft)` | structured draft | `list[Claim]` | 无／受控模型可选 | 每个分析点有稳定 claim_no 和 evidence_ids |
| `citation_validator.py::validate_claim(claim, bundle, context)` | Claim＋EvidenceBundle＋业务上下文 | `ClaimValidation` | DocumentRepo、PolicyStatus、EntailmentGateway | 校验 span、快照、日期、地区、主体、语义支持 |
| `citation_validator.py::validate_draft(draft, bundle)` | DraftOutput | `ValidatedDraft` | claim validator | 无来源关键主张 blocked；不得自行造文号／URL |
| `confidence.py::calculate_dimensions(input)` | facts、sources、conflicts、rules、citations、review | ConfidenceDimensions | 纯规则 | 不输出伪精确百分比；保存降级原因 |
| `service.py::persist_validated_draft(command)` | ValidatedDraft、run | DraftDetail | DraftRepo、UoW、ReviewService | 默认 pending_review；生成与用户编辑产生新版本 |

`generation/models.py` 固定映射 `answer_drafts`、`answer_claims`、`claim_evidences`；不得放在对话消息表中混存。

### 5.14 Reviews

| 文件／Function | 入参 | 出参 | 依赖 | 契约 |
|---|---|---|---|---|
| `service.py::create_review_task(command)` | resource type／id、submitter、assignee | ReviewTask | ReviewRepo、UoW | 同一资源版本只允许一个 active task |
| `service.py::get_review_package(task_id, principal)` | task | `ReviewPackage` | Case／Draft／Evidence／Rule repos | 只返回审核所需、按权限脱敏的内容 |
| `service.py::record_action(command, principal)` | task、decision、target、comment、expected version | ReviewResult | ReviewRepo、Resource service、UoW、Audit | append-only；自审／职责分离；逐主张审核 |
| `domain.py::aggregate_decisions(actions)` | action list | overall decision | 纯函数 | 任一关键主张 return/reject 则整体不可 approve |

`models.py` 映射 `review_tasks`、`review_actions`。

### 5.15 Feedback & Audit

| 文件／Function | 入参 | 出参 | 依赖 | 契约 |
|---|---|---|---|---|
| `feedback/service.py::create_ticket(command, principal)` | source type/id、category、description、severity | FeedbackTicket | Source access verifier、FeedbackRepo、Redactor、UoW | 用户只能反馈可见资源；正文脱敏 |
| `feedback/service.py::resolve_ticket(command, principal)` | ticket、resolution、linked knowledge object、version | FeedbackTicket | FeedbackRepo、KnowledgeService、UoW、Audit | 反馈不能直接改正式知识，只能关联修订流程 |
| `audit/service.py::record(event)` | AuditEvent | None | AuditRepo | 追加式、失败对关键写操作应触发事务／Outbox策略 |
| `audit/service.py::search(query, principal)` | resource、action、actor、time、cursor | Page[AuditView] | AuditRepo | 只有 auditor/admin；敏感内容只显示摘要 |

`feedback/models.py` 映射 `feedback_tickets`；`audit/models.py` 映射 `audit_logs`。

---

## 6. Infrastructure Adapter 契约

### 6.1 MySQL

| 文件／Function | 契约 |
|---|---|
| `base.py::Base` | 所有 ORM metadata 根；migration 加载模块模型，不在运行时 create_all |
| `session.py::create_engine(settings)` | 返回 AsyncEngine；pool_pre_ping、连接回收、SQL 日志脱敏 |
| `session.py::session_factory(engine)` | async sessionmaker，`expire_on_commit=False` |
| `uow.py::SqlAlchemyUnitOfWork` | 请求／任务级 Session；commit 同时保存 outbox event |
| `outbox.py::claim_events(limit, worker)` | `FOR UPDATE SKIP LOCKED` 或等效方案；返回可处理批次 |
| `outbox.py::mark_done(event_id)` | 幂等完成；失败记录 safe error 和 next_attempt_at |

### 6.2 Redis

| 文件／Function | 入参／出参 | 约束 |
|---|---|---|
| `client.py::create_redis(settings)` | Settings→Redis client | decode 策略固定；健康检查；关闭连接 |
| `keyspace.py::session_key(org, conversation)` | IDs→str | 所有 key 必须含 `tm:` 前缀；租户 key 含 org_id |
| `cache.py::get_json(key, type)` | key、Pydantic type→T／None | JSON schema 校验失败当 cache miss，不污染业务 |
| `cache.py::set_json(key, value, ttl)` | — | 正 TTL 必填；禁止无期限政策缓存 |
| `checkpoint.py::save_checkpoint(thread, version, state)` | — | CAS／版本校验；大对象仅存引用 |
| `checkpoint.py::append_run_event(run, event)` | — | event_id 单调；24h TTL；支持 Last-Event-ID |

### 6.3 Milvus

| 文件／Function | 入参／出参 | 约束 |
|---|---|---|
| `client.py::create_milvus_client(settings)` | Settings→client | database／token 不从请求传入 |
| `collections.py::ensure_collection(spec)` | CollectionSpec→None | 只在 admin／bootstrap 命令执行，不在每次请求执行 |
| `collections.py::switch_alias(alias, collection)` | — | smoke test 后原子切换；记录 snapshot |
| `search.py::search_dense(query_vector, filters, top_k)` | vector＋typed filters→candidates | 服务端构造 filter，客户端不得传表达式 |
| `search.py::search_sparse(query_text, filters, top_k)` | text＋filters→candidates | BM25 analyzer／tokenizer 版本记录 |
| `search.py::hybrid_search(...)` | query＋filters＋limits→rank sets | 返回各通道 rank，不隐藏原始分数 |
| `search.py::upsert_records(records, idempotency_key)` | projection records | checksum 幂等；只写 published snapshot |

### 6.4 Neo4j

| 文件／Function | 入参／出参 | 约束 |
|---|---|---|
| `client.py::create_driver(settings)` | Settings→AsyncDriver | database 显式；连接生命周期统一 |
| `templates.py::get_template(route_code, expansion_type)` | 枚举→CypherTemplate | 只返回代码内白名单，不接收用户 Cypher |
| `graph_store.py::expand(anchors, template, limits)` | typed anchors→EvidencePaths | 最大深度／节点／超时；去环；每条边有 source_chunk_id |
| `graph_store.py::upsert_batch(batch)` | published projection | relation_id 唯一，按 publish batch 幂等 |
| `graph_store.py::retire_batch(batch_id)` | batch | 只停用目标 batch，不误删共享受控节点 |

### 6.5 MinIO

| 文件／Function | 入参／出参 | 约束 |
|---|---|---|
| `client.py::create_minio(settings)` | Settings→client | endpoint 与 secure 分离，禁止保存永久公网 URL |
| `object_store.py::put_stream(bucket, key, stream, metadata)` | stream→ObjectRef | 流式上传、大小／MIME／hash 校验 |
| `object_store.py::get_stream(ref)` | ObjectRef→async stream | 权限和 object hash 可选复核 |
| `object_store.py::presign_get(ref, ttl)` | ObjectRef→short URL | ttl 上限；下载另写审计 |
| `object_store.py::copy_immutable(source, target)` | refs | 原件不得被覆盖；存在且 hash 不同则冲突 |

### 6.6 Model Gateway

| 文件／Function | 入参／出参 | 约束 |
|---|---|---|
| `gateway.py::LLMGateway.generate_structured(request, schema)` | PromptRequest＋JSON Schema→ModelResult | 统一 timeout、token、重试、model version；原始响应受控保存 |
| `gateway.py::EmbeddingGateway.embed(texts, version)` | list[str]→vectors | batch、维度校验、顺序不变 |
| `gateway.py::RerankerGateway.rerank(query, docs)` | query＋docs→scores | 输入输出数量一致；失败显式 degraded |
| `dashscope_llm.py` | 实现 LLMGateway | 不把 API key 写日志；429／5xx 分类 |
| `bge_embedder.py` | 本地／服务化 BGE adapter | 输出固定 1024 维；模型版本进入投影 |
| `bge_reranker.py` | reranker adapter | 控制最大文档数和长度 |

### 6.7 HTTP、Security、Telemetry

| 文件 | 核心契约 |
|---|---|
| `http/client.py` | `request_with_policy()` 统一 timeout、重试、User-Agent、最大响应和 safe log |
| `http/official_source.py` | 白名单域名、robots／速率策略、条件请求；不绕过访问控制 |
| `security/tokens.py` | `issue_access_token`、`verify_access_token`、`rotate_refresh_token`；JWT claims 包含 user、org、session、roles、exp、jti |
| `security/passwords.py` | Argon2 hash／verify；可透明升级 hash 参数 |
| `security/redaction.py` | `detect_sensitive`、`redact_text`；返回命中类型和脱敏文本，不保存原始敏感值 |
| `telemetry/metrics.py` | API、workflow、retrieval、projection、model 指标；标签禁止 org name／query text |
| `telemetry/tracing.py` | request_id／run_id 跨 API、Worker、模型传播；span 不含完整正文 |

---

## 7. Worker、Scheduler 与任务契约

### 7.1 Worker 文件

| 文件／Function | 契约 |
|---|---|
| `celery_app.py::create_celery(settings)` | 返回 Celery app；JSON serializer；禁用 pickle；设置 task time limit／acks_late／prefetch |
| `task_registry.py::register_tasks(app)` | 显式 import 各模块 tasks；避免魔法 autodiscover 漏任务 |
| `signals.py::setup_task_context(...)` | 每任务创建 request/task ID、日志上下文和资源清理 |

### 7.2 Queue 与任务

| Queue | Task 名 | Payload | 成功输出 | 重试 |
|---|---|---|---|---|
| ingestion | `sources.run_job.v1` | job_id、schema_version | discovered／changed count | 网络、429、5xx；指数退避 |
| parsing | `documents.parse.v1` | document_version_id | chunk count、warnings | 临时 I/O；解析格式错误不无限重试 |
| parsing | `documents.ocr.v1` | object_ref、page range | OCR object ref | 单独并发／超时 |
| knowledge | `knowledge.extract.v1` | document_version_id、prompt_version | candidate batch ID | 模型临时错误 |
| embedding | `projection.policy.v1` | event_id、snapshot、embedding_version | sync state | 幂等，死信告警 |
| embedding | `projection.faq.v1` | faq_version、org snapshot | sync state | 幂等 |
| graph_sync | `projection.graph.v1` | publish_batch、event_id | sync state | 同 aggregate 串行 |
| evaluation | `evaluation.golden.v1` | snapshot、suite version | report object ref | 可人工重跑 |
| maintenance | `outbox.dispatch.v1` | batch limit | processed count | 周期任务 |
| maintenance | `projections.verify.v1` | snapshot | drift report | 不自动删除修复 |

### 7.3 Scheduler

`beat_schedule.py::build_schedule(settings) -> dict` 只声明：白名单低频增量采集、Outbox dispatch、死信提醒、投影巡检、过期缓存／临时对象清理和定时评测。生产实际 cron 通过环境覆盖；代码默认值必须保守，不能高频抓取官方站点。

---

## 8. Frontend 文件与 Function 契约

### 8.1 App 与 API

| 文件／Function | 入参 | 出参 | 依赖／约束 |
|---|---|---|---|
| `main.tsx::bootstrap()` | DOM root | render app | 初始化 QueryClient、Router、ErrorBoundary；失败显示可恢复页 |
| `providers.tsx::AppProviders({children})` | ReactNode | Provider tree | 顺序固定：Error→Auth→Query→Theme→Router |
| `router.tsx::createAppRouter()` | 无 | Router | route lazy load、权限 meta、NotFound |
| `permissions.ts::can(principal, permission)` | Principal、code | boolean | 只用于 UI；后端仍强制校验 |
| `api/client.ts::request<T>(path, options)` | path、method、body、schema 可选 | `Promise<T>` | 自动 Bearer、X-Request-ID、refresh single-flight、ErrorEnvelope 映射 |
| `api/errors.ts::toAppError(response)` | HTTP／network error | AppError | 保留 code、safe message、details、retryable、request_id |
| `api/sse.ts::openRunEventStream(options)` | run_id、Bearer、lastEventId、AbortSignal、onEvent | `Promise<void>` | 使用 fetch 流，不把 token 放 URL；解析跨 chunk 行；schema 校验 |

### 8.2 Stores 与 Hooks

| 文件／Function | 契约 |
|---|---|
| `auth-store.ts::setSession(principal, accessToken)` | access token 仅内存；refresh token 由 HttpOnly cookie 管理 |
| `auth-store.ts::clearSession(reason)` | 清空认证缓存和机构级 Query cache |
| `run-store.ts::applyEvent(event)` | 按 event_id 去重和顺序应用；只存当前 run 瞬时 UI，不替代服务端状态 |
| `use-permission.ts::usePermission(code)` | 返回 boolean；无 principal 为 false |
| `use-run-stream.ts::useRunStream(runId)` | 管理 AbortController、重连、Last-Event-ID；完成后 invalidate run／draft queries |

### 8.3 Feature 目录标准

每个 `features/<name>` 默认包含：

```text
features/<name>/
├── api.ts          # 调用 generated client／request
├── queries.ts      # TanStack Query key、query／mutation hooks
├── types.ts        # 仅 UI 派生类型，不复制 API DTO
├── components/     # 领域局部组件
└── index.ts        # 对外公开入口
```

只有 conversation 可额外有 `stream.ts`，knowledge／reviews 可有 `forms.ts`。禁止各 feature 自建 HTTP client、认证逻辑或 SSE parser。

### 8.4 主要 Feature 契约

| Feature／Function | 入参 | 出参 | 说明 |
|---|---|---|---|
| `cases/api.ts::createCase(input)` | generated CreateCaseRequest | CaseDetail | 成功后写入 case query cache |
| `cases/queries.ts::useCase(caseId)` | ID | QueryResult<CaseDetail> | key 含 current org |
| `cases/api.ts::confirmFacts(input)` | case／profile／fact decisions | FactConfirmationResult | 成功使旧 run／draft cache stale |
| `conversation/api.ts::submitQuery(input)` | case、conversation、question、profile | RunAccepted | 使用 Idempotency-Key |
| `conversation/components/FactQuestionCard` | missing facts、checkpoint | 用户确认事件 | 不把未确认值显示为已知事实 |
| `conversation/components/RunTimeline` | SSE events | 阶段列表 | 不显示内部思维链 |
| `policies/api.ts::searchPolicies(filters)` | q、doc no、region、date、status | Policy result page | 无 business_date 时显示“当前状态”提示 |
| `policies/components/EvidenceDrawer` | EvidenceRef | 原文定位视图 | URL／文号来自结构化字段，不解析生成文本 |
| `faq/api.ts::searchFaq(filters)` | q、scope、region、date | FAQ candidates | 展示证据状态和 FAQ 级别 |
| `risk/components/RiskFindingCard` | RiskFinding | 卡片 | 显示 rule code/version、触发事实、缺失事实、证据 |
| `procedures/components/ProcedureCard` | ProcedureDetail | 卡片／清单 | national_only 明显提示；unknown 材料条件不能隐藏 |
| `reviews/api.ts::recordAction(input)` | decision、target、comment、version | ReviewResult | 409 时加载最新审核包而非覆盖 |
| `knowledge/api.ts::activateBatch(input)` | batch、expected snapshot | Snapshot | 二次确认；显示异步投影／验证状态 |

### 8.5 Pages

| 页面 | 组合内容 | 页面不得承担 |
|---|---|---|
| `LoginPage` | 登录、机构选择 | 保存 refresh token 到 localStorage |
| `CaseListPage` | 筛选、分页、创建事项 | 直接触发模型 |
| `CaseWorkspacePage` | 左侧画像／历史，中部对话和结果，右侧证据／草稿 | 把所有后台管理功能塞进对话流 |
| `PolicySearchPage` | 多条件检索和结果卡 | 默认推断客户适用 |
| `PolicyDetailPage` | 原文、版本、沿革、关系 | 以图谱路径代替原文证据 |
| `FaqPage` | FAQ 搜索；知识角色可编辑 | 普通用户直接发布 FAQ |
| `ProcedurePage` | 地区化事项卡 | 模拟电子税务局 |
| `ReviewQueuePage` | 分派、优先级、状态 | 审核正文 |
| `ReviewDetailPage` | 事实、主张、证据、规则、版本对比、决策 | 静默修改原始草稿 |
| `KnowledgeOpsPage` | 来源、任务、候选、FAQ、规则、批次、快照 | 绕过验证直接写 Milvus／Neo4j |
| `AuditPage` | 审计查询与脱敏详情 | 允许修改日志 |

---

## 9. Contracts 目录

### 9.1 生成方向

1. 后端 Pydantic／FastAPI 导出 `taxmind-v1.openapi.json`。
2. `generate-web-client.sh` 从 OpenAPI 生成 `apps/web/src/api/generated`。
3. SSE、风险 DSL、生成输出和 EvidenceBundle 使用独立 JSON Schema，因为它们不全是同步 HTTP body。
4. Contract test 验证后端实际输出、示例文件和前端 parser 使用同一 schema_version。

### 9.2 Schema 版本

- API 版本放 URL：`/api/v1`；兼容字段可在 v1 内追加。
- Event／task payload 有 `schema_version: 1`；消费者拒绝未知 major。
- JSON Schema `$id` 使用稳定 URI 形式，不绑定本地路径。
- 删除字段、改变语义或改变枚举必须升 major，不靠前端容错掩盖。

---

## 10. 测试目录与 Fixture 契约

| 目录 | 内容 | 外部依赖 |
|---|---|---|
| `apps/backend/tests/unit` | 领域状态、DSL、RRF、日期／地区、脱敏、服务 fake repo | 无容器／网络 |
| `integration` | Repository、Outbox、Redis、Milvus、Neo4j、MinIO adapter | Testcontainers 或 Compose test profile |
| `contract` | HTTP／SSE／task／schema | 测试 App＋schema files |
| `golden` | 七路由、四态、引用、拒答、规则 | 固定快照和模型 mock／受控模型配置 |
| `security` | 跨租户、越权、注入、恶意文件、敏感数据 | 测试 App 和隔离存储 |
| `tests/e2e` | 浏览器 P0 主流程 | Playwright＋完整 test stack |

Fixture 规则：

- `official-documents` 仅放少量允许测试使用的官方公开片段及来源说明，不放整库。
- `synthetic-cases` 明确标记 `data_classification=SYNTHETIC`。
- 测试 ID 和时间固定；测试禁止依赖当前真实日期。
- 模型调用默认 fake；需要真实模型的评测使用显式 marker 和预算开关，CI 默认不执行。

---

## 11. 基础配置文件模板

以下模板是 Codex 首次落盘内容。注释说明可以保留；其中版本范围由 lockfile 固化。

### 11.1 `.python-version`

```text
3.12
```

### 11.2 `.nvmrc`

```text
24
```

### 11.3 根 `package.json`

```json
{
  "name": "taxmind-pro",
  "private": true,
  "packageManager": "pnpm@11.14.0",
  "engines": {
    "node": ">=24 <25",
    "pnpm": ">=11 <12"
  },
  "scripts": {
    "dev:web": "pnpm --filter @taxmind/web dev",
    "build:web": "pnpm --filter @taxmind/web build",
    "lint:web": "pnpm --filter @taxmind/web lint",
    "test:web": "pnpm --filter @taxmind/web test",
    "typecheck:web": "pnpm --filter @taxmind/web typecheck",
    "generate:client": "bash scripts/generate-web-client.sh"
  }
}
```

### 11.4 `pnpm-workspace.yaml`

```yaml
packages:
  - apps/web

minimumReleaseAge: 1440
```

`minimumReleaseAge` 设置 24 小时供应链缓冲；紧急安全修复可在评审后显式覆盖，不应为了安装方便删除。

### 11.5 `.editorconfig`

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 2

[*.py]
indent_size = 4

[Makefile]
indent_style = tab

[*.md]
trim_trailing_whitespace = false
```

### 11.6 `.gitattributes`

```gitattributes
* text=auto eol=lf
*.sh text eol=lf
*.py text eol=lf
*.ts text eol=lf
*.tsx text eol=lf
*.json text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.pdf binary
*.png binary
*.jpg binary
*.jpeg binary
```

### 11.7 `.gitignore`

```gitignore
# secrets and local overrides
.env
.env.*
!.env.example
compose.override.yaml

# Python
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.venv/
dist/
build/
*.egg-info/

# Node
node_modules/
apps/web/dist/
apps/web/.vite/
playwright-report/
test-results/

# IDE / OS
.idea/
.vscode/
.DS_Store
Thumbs.db

# runtime data and models
.data/
.cache/
models/
logs/
exports/

# generated API client is regenerated in CI
apps/web/src/api/generated/*
!apps/web/src/api/generated/.gitkeep
```

是否提交 `api/generated` 必须二选一。本文选择“不提交生成代码、CI 现生成并检查”；若团队更重视开箱即用，可提交生成产物，但 CI 必须验证其没有漂移，不能一部分提交一部分忽略。

### 11.8 `.env.example`

```dotenv
# Application
APP_NAME=TaxMind Pro
APP_ENV=development
APP_DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api/v1
WEB_ORIGIN=http://localhost:5173
LOG_LEVEL=INFO
LOG_JSON=false

# Security: replace in local .env; production must use a secret manager
JWT_SECRET=replace-with-at-least-32-random-bytes
JWT_ALGORITHM=HS256
JWT_ISSUER=taxmind-pro
ACCESS_TOKEN_TTL_MINUTES=30
REFRESH_TOKEN_TTL_DAYS=14
STREAM_REPLAY_TTL_SECONDS=86400

# MySQL
MYSQL_IMAGE=mysql:8.4
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=taxmind
MYSQL_USER=taxmind
MYSQL_PASSWORD=taxmind-dev-only
MYSQL_ROOT_PASSWORD=root-dev-only
MYSQL_POOL_SIZE=10
MYSQL_MAX_OVERFLOW=20

# Redis / Celery
REDIS_IMAGE=redis:7.4-alpine
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/2
SHORT_MEMORY_TTL_SECONDS=259200
PUBLIC_CACHE_TTL_SECONDS=600

# MinIO
MINIO_IMAGE=quay.io/minio/minio:RELEASE.2025-04-22T22-12-26Z
MINIO_MC_IMAGE=quay.io/minio/mc:RELEASE.2025-04-16T18-13-26Z
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_ACCESS_KEY=taxmind-minio
MINIO_SECRET_KEY=taxmind-minio-dev-only
MINIO_SECURE=false
MINIO_RAW_BUCKET=taxmind-raw
MINIO_PARSED_BUCKET=taxmind-parsed
MINIO_EXPORTS_BUCKET=taxmind-exports
MINIO_TEMP_BUCKET=taxmind-temp

# Milvus / etcd
ETCD_IMAGE=quay.io/coreos/etcd:v3.5.18
MILVUS_IMAGE=milvusdb/milvus:v2.6.4
MILVUS_URI=http://127.0.0.1:19530
MILVUS_TOKEN=
MILVUS_DATABASE=taxmind
MILVUS_POLICY_ALIAS=policy_chunks_current
MILVUS_FAQ_ALIAS=faq_questions_current
MILVUS_CASE_ALIAS=approved_case_memories_current
EMBEDDING_DIMENSION=1024

# Neo4j
NEO4J_IMAGE=neo4j:5.26-community
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=taxmind-neo4j-dev-only
NEO4J_DATABASE=neo4j
NEO4J_QUERY_TIMEOUT_SECONDS=5
NEO4J_MAX_PATH_DEPTH=4

# Models
DASHSCOPE_API_KEY=replace-me
DASHSCOPE_LLM_MODEL=replace-with-approved-model
DASHSCOPE_TEMPERATURE=0.1
LLM_TIMEOUT_SECONDS=45
LLM_MAX_RETRIES=2
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_MODEL_VERSION=initial
RERANKER_PROVIDER=local
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RERANKER_MODEL_VERSION=initial
MODEL_DEVICE=auto

# Retrieval
DENSE_TOP_K=30
SPARSE_TOP_K=30
FAQ_TOP_K=10
RERANK_CANDIDATE_LIMIT=40
EVIDENCE_LIMIT=12
RRF_K=60

# Ingestion safety
INGESTION_USER_AGENT=TaxMindProKnowledgeBot/0.1 contact=replace-me
INGESTION_MAX_BYTES=52428800
INGESTION_REQUESTS_PER_MINUTE_PER_DOMAIN=6
INGESTION_CONNECT_TIMEOUT_SECONDS=5
INGESTION_READ_TIMEOUT_SECONDS=20

# Observability
OTEL_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
METRICS_ENABLED=true
```

`Settings` 不应要求同时提供 DSN 与离散字段，避免配置冲突。由 `settings.py` 使用离散字段构造 DSN；日志输出 DSN 时必须遮盖密码。

### 11.9 `apps/backend/pyproject.toml`

```toml
[build-system]
requires = ["hatchling>=1.27,<2"]
build-backend = "hatchling.build"

[project]
name = "taxmind-backend"
version = "0.1.0"
description = "TaxMind Pro modular monolith backend"
requires-python = ">=3.12,<3.13"
dependencies = [
  "fastapi>=0.116,<1",
  "uvicorn[standard]>=0.35,<1",
  "pydantic>=2.11,<3",
  "pydantic-settings>=2.10,<3",
  "sqlalchemy[asyncio]>=2.0.41,<3",
  "alembic>=1.16,<2",
  "asyncmy>=0.2.10,<1",
  "redis>=6.2,<7",
  "celery>=5.5,<6",
  "langgraph>=1,<2",
  "pymilvus>=2.6,<3",
  "neo4j>=5.26,<7",
  "minio>=7.2,<8",
  "dashscope>=1.24,<2",
  "httpx>=0.28,<1",
  "beautifulsoup4>=4.13,<5",
  "lxml>=6,<7",
  "pymupdf>=1.26,<2",
  "orjson>=3.11,<4",
  "python-multipart>=0.0.20,<1",
  "pyjwt[crypto]>=2.10,<3",
  "pwdlib[argon2]>=0.2,<1",
  "structlog>=25.4,<26",
  "tenacity>=9.1,<10",
  "prometheus-client>=0.22,<1",
  "opentelemetry-api>=1.36,<2",
  "opentelemetry-sdk>=1.36,<2",
  "opentelemetry-instrumentation-fastapi>=0.57b0,<1"
]

[project.optional-dependencies]
local-models = [
  "sentence-transformers>=5,<6",
  "torch>=2.7,<3"
]

[dependency-groups]
dev = [
  "pytest>=8.4,<9",
  "pytest-asyncio>=1,<2",
  "pytest-cov>=6.2,<7",
  "mypy>=1.17,<2",
  "ruff>=0.12,<1",
  "respx>=0.22,<1",
  "freezegun>=1.5,<2",
  "testcontainers[mysql,redis]>=4.12,<5",
  "types-pyjwt>=1.7,<2"
]

[tool.hatch.build.targets.wheel]
packages = ["src/taxmind"]

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "ASYNC", "S", "SIM", "RUF"]
ignore = ["S101"]

[tool.ruff.lint.isort]
known-first-party = ["taxmind"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
packages = ["taxmind"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
  "integration: requires local infrastructure",
  "golden: runs the governed evaluation suite",
  "external_model: calls a configured external model"
]
addopts = "-q --strict-markers --disable-warnings"

[tool.coverage.run]
branch = true
source = ["taxmind"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

依赖版本是允许范围，不是最终精确版本；首次 `uv lock` 后以 `uv.lock` 为唯一安装真相。`local-models` 必须是可选 extra，避免 API／Worker 所有镜像无条件携带 PyTorch。

### 11.10 `apps/web/package.json`

```json
{
  "name": "@taxmind/web",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "engines": {
    "node": ">=24 <25"
  },
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint . --max-warnings=0",
    "typecheck": "tsc -b --pretty false",
    "test": "vitest run",
    "test:watch": "vitest",
    "generate:types": "openapi-typescript ../../packages/contracts/openapi/taxmind-v1.openapi.json -o src/api/generated/schema.d.ts"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.85.0",
    "antd": "^5.27.0",
    "dayjs": "^1.11.13",
    "dompurify": "^3.2.6",
    "marked": "^16.2.0",
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "react-router-dom": "^7.8.0",
    "zod": "^4.1.0",
    "zustand": "^5.0.8"
  },
  "devDependencies": {
    "@eslint/js": "^9.34.0",
    "@testing-library/jest-dom": "^6.8.0",
    "@testing-library/react": "^16.3.0",
    "@types/node": "^24.3.0",
    "@types/react": "^19.1.12",
    "@types/react-dom": "^19.1.9",
    "@vitejs/plugin-react": "^6.0.0",
    "eslint": "^9.34.0",
    "eslint-plugin-react-hooks": "^5.2.0",
    "eslint-plugin-react-refresh": "^0.4.20",
    "globals": "^16.3.0",
    "jsdom": "^26.1.0",
    "openapi-typescript": "^7.9.0",
    "typescript": "^5.9.2",
    "typescript-eslint": "^8.41.0",
    "vite": "^8.1.0",
    "vitest": "^4.0.0"
  }
}
```

如果某个精确包版本不存在，Codex 不得随意降级整个技术栈；应先以当前 registry 验证同一 major 的可用 patch，再更新文档和 lockfile。脚手架验收以 lockfile 成功解析和测试通过为准。

### 11.11 `apps/web/tsconfig.json`

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" }
  ]
}
```

### 11.12 `apps/web/tsconfig.app.json`

```json
{
  "compilerOptions": {
    "target": "ES2023",
    "useDefineForClassFields": true,
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src", "vite.config.ts"]
}
```

### 11.13 `apps/web/vite.config.ts`

```ts
import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      sourcemap: mode !== 'production',
      target: 'es2023',
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'html'],
      },
    },
  };
});
```

### 11.14 `apps/web/eslint.config.js`

```js
import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'src/api/generated'] },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2023,
      globals: globals.browser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
    },
  },
);
```

### 11.15 `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-added-large-files
        args: [--maxkb=2048]
      - id: check-merge-conflict
      - id: check-json
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace
        exclude: '\.md$'
      - id: detect-private-key

  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check
        entry: bash -c 'cd apps/backend && uv run ruff check src tests'
        language: system
        types: [python]
        pass_filenames: false
      - id: ruff-format
        name: ruff format check
        entry: bash -c 'cd apps/backend && uv run ruff format --check src tests'
        language: system
        types: [python]
        pass_filenames: false
```

前端完整 lint 不放 pre-commit，以免每次提交重复启动 Node 工具链；CI 必须执行。提交前可手动运行 `make check`。

### 11.16 `Makefile`

```makefile
SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help bootstrap infra-up infra-down api worker scheduler web migrate \
        lint format typecheck test test-integration test-golden contracts check

help:
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "%-24s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: ## Install backend and frontend dependencies
	cd apps/backend && uv sync --all-groups
	pnpm install --frozen-lockfile=false

infra-up: ## Start local infrastructure
	docker compose up -d mysql redis minio minio-init etcd milvus neo4j

infra-down: ## Stop local stack without deleting volumes
	docker compose down

api: ## Run FastAPI with reload
	cd apps/backend && uv run uvicorn taxmind.entrypoints.api.main:create_app --factory --reload --port 8000

worker: ## Run Celery worker
	cd apps/backend && uv run celery -A taxmind.entrypoints.worker.celery_app:app worker -l INFO

scheduler: ## Run Celery beat
	cd apps/backend && uv run celery -A taxmind.entrypoints.worker.celery_app:app beat -l INFO

web: ## Run React dev server
	pnpm --filter @taxmind/web dev

migrate: ## Apply database migrations
	cd apps/backend && uv run alembic upgrade head

lint: ## Run backend and frontend linters
	cd apps/backend && uv run ruff check src tests
	pnpm lint:web

format: ## Format backend code
	cd apps/backend && uv run ruff format src tests
	cd apps/backend && uv run ruff check --fix src tests

typecheck: ## Run Python and TypeScript type checks
	cd apps/backend && uv run mypy src
	pnpm typecheck:web

test: ## Run fast unit and contract tests
	cd apps/backend && uv run pytest -m 'not integration and not golden and not external_model'
	pnpm test:web

test-integration: ## Run backend integration tests
	cd apps/backend && uv run pytest -m integration

test-golden: ## Run governed golden evaluation
	cd apps/backend && uv run pytest -m golden

contracts: ## Export OpenAPI and generate web types
	bash scripts/export-openapi.sh
	bash scripts/generate-web-client.sh

check: lint typecheck test ## Run the local merge gate
```

`infra-down` 不删除 volume。若需要清空演示数据，必须提供明确的 `reset-demo` 脚本、列出目标 volume 并二次确认；不要把 `docker compose down -v` 包装成普通命令。

### 11.17 `compose.yaml`

```yaml
name: taxmind-pro

services:
  mysql:
    image: ${MYSQL_IMAGE:-mysql:8.4}
    environment:
      MYSQL_DATABASE: ${MYSQL_DATABASE:-taxmind}
      MYSQL_USER: ${MYSQL_USER:-taxmind}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-taxmind-dev-only}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-root-dev-only}
      TZ: UTC
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_0900_ai_ci
    ports:
      - "${MYSQL_EXPOSE_PORT:-3306}:3306"
    volumes:
      - mysql-data:/var/lib/mysql
    healthcheck:
      test: [CMD-SHELL, "mysqladmin ping -h 127.0.0.1 -u root -p$$MYSQL_ROOT_PASSWORD --silent"]
      interval: 5s
      timeout: 5s
      retries: 30
    networks: [taxmind]

  redis:
    image: ${REDIS_IMAGE:-redis:7.4-alpine}
    command: [redis-server, --appendonly, "yes"]
    ports:
      - "${REDIS_EXPOSE_PORT:-6379}:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: [CMD, redis-cli, ping]
      interval: 5s
      timeout: 3s
      retries: 30
    networks: [taxmind]

  minio:
    image: ${MINIO_IMAGE:-quay.io/minio/minio:RELEASE.2025-04-22T22-12-26Z}
    command: server /data --console-address :9001
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-taxmind-minio}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-taxmind-minio-dev-only}
    ports:
      - "${MINIO_API_EXPOSE_PORT:-9000}:9000"
      - "${MINIO_CONSOLE_EXPOSE_PORT:-9001}:9001"
    volumes:
      - minio-data:/data
    healthcheck:
      test: [CMD-SHELL, "curl -fsS http://localhost:9000/minio/health/live || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 30
    networks: [taxmind]

  minio-init:
    image: ${MINIO_MC_IMAGE:-quay.io/minio/mc:RELEASE.2025-04-16T18-13-26Z}
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: /bin/sh
    command: >-
      -c "mc alias set local http://minio:9000
      $${MINIO_ROOT_USER} $${MINIO_ROOT_PASSWORD} &&
      mc mb --ignore-existing local/$${MINIO_RAW_BUCKET} &&
      mc mb --ignore-existing local/$${MINIO_PARSED_BUCKET} &&
      mc mb --ignore-existing local/$${MINIO_EXPORTS_BUCKET} &&
      mc mb --ignore-existing local/$${MINIO_TEMP_BUCKET} &&
      mc mb --ignore-existing local/milvus-bucket"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-taxmind-minio}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-taxmind-minio-dev-only}
      MINIO_RAW_BUCKET: ${MINIO_RAW_BUCKET:-taxmind-raw}
      MINIO_PARSED_BUCKET: ${MINIO_PARSED_BUCKET:-taxmind-parsed}
      MINIO_EXPORTS_BUCKET: ${MINIO_EXPORTS_BUCKET:-taxmind-exports}
      MINIO_TEMP_BUCKET: ${MINIO_TEMP_BUCKET:-taxmind-temp}
    networks: [taxmind]

  etcd:
    image: ${ETCD_IMAGE:-quay.io/coreos/etcd:v3.5.18}
    environment:
      ETCD_AUTO_COMPACTION_MODE: revision
      ETCD_AUTO_COMPACTION_RETENTION: "1000"
      ETCD_QUOTA_BACKEND_BYTES: "4294967296"
      ETCD_SNAPSHOT_COUNT: "50000"
    command: >-
      etcd --advertise-client-urls=http://127.0.0.1:2379
      --listen-client-urls=http://0.0.0.0:2379
      --data-dir=/etcd
    volumes:
      - etcd-data:/etcd
    healthcheck:
      test: [CMD, etcdctl, endpoint, health]
      interval: 5s
      timeout: 3s
      retries: 30
    networks: [taxmind]

  milvus:
    image: ${MILVUS_IMAGE:-milvusdb/milvus:v2.6.4}
    command: [milvus, run, standalone]
    security_opt:
      - seccomp:unconfined
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
      MINIO_ACCESS_KEY_ID: ${MINIO_ACCESS_KEY:-taxmind-minio}
      MINIO_SECRET_ACCESS_KEY: ${MINIO_SECRET_KEY:-taxmind-minio-dev-only}
      COMMON_STORAGETYPE: minio
    depends_on:
      etcd:
        condition: service_healthy
      minio-init:
        condition: service_completed_successfully
    ports:
      - "${MILVUS_EXPOSE_PORT:-19530}:19530"
      - "${MILVUS_HEALTH_EXPOSE_PORT:-9091}:9091"
    volumes:
      - milvus-data:/var/lib/milvus
    healthcheck:
      test: [CMD-SHELL, "curl -fsS http://localhost:9091/healthz || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 30
    networks: [taxmind]

  neo4j:
    image: ${NEO4J_IMAGE:-neo4j:5.26-community}
    environment:
      NEO4J_AUTH: ${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD:-taxmind-neo4j-dev-only}
      NEO4J_server_memory_heap_initial__size: 512m
      NEO4J_server_memory_heap_max__size: 1G
      NEO4J_server_memory_pagecache_size: 512m
    ports:
      - "${NEO4J_HTTP_EXPOSE_PORT:-7474}:7474"
      - "${NEO4J_BOLT_EXPOSE_PORT:-7687}:7687"
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs
    healthcheck:
      test: [CMD-SHELL, "wget -qO- http://localhost:7474 >/dev/null || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 30
    networks: [taxmind]

  backend:
    profiles: [app]
    build:
      context: .
      dockerfile: infra/docker/backend.Dockerfile
    env_file: [.env]
    environment:
      MYSQL_HOST: mysql
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
      MINIO_ENDPOINT: minio:9000
      MILVUS_URI: http://milvus:19530
      NEO4J_URI: bolt://neo4j:7687
    command: uv run uvicorn taxmind.entrypoints.api.main:create_app --factory --host 0.0.0.0 --port 8000
    ports:
      - "${API_EXPOSE_PORT:-8000}:8000"
    depends_on:
      mysql: { condition: service_healthy }
      redis: { condition: service_healthy }
      milvus: { condition: service_healthy }
      neo4j: { condition: service_healthy }
    networks: [taxmind]

  worker:
    profiles: [app]
    build:
      context: .
      dockerfile: infra/docker/backend.Dockerfile
    env_file: [.env]
    environment:
      MYSQL_HOST: mysql
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
      MINIO_ENDPOINT: minio:9000
      MILVUS_URI: http://milvus:19530
      NEO4J_URI: bolt://neo4j:7687
    command: uv run celery -A taxmind.entrypoints.worker.celery_app:app worker -l INFO
    depends_on:
      mysql: { condition: service_healthy }
      redis: { condition: service_healthy }
    networks: [taxmind]

  scheduler:
    profiles: [app]
    build:
      context: .
      dockerfile: infra/docker/backend.Dockerfile
    env_file: [.env]
    environment:
      MYSQL_HOST: mysql
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
      MINIO_ENDPOINT: minio:9000
      MILVUS_URI: http://milvus:19530
      NEO4J_URI: bolt://neo4j:7687
    command: uv run celery -A taxmind.entrypoints.worker.celery_app:app beat -l INFO
    depends_on:
      redis: { condition: service_healthy }
    networks: [taxmind]

  web:
    profiles: [app]
    build:
      context: .
      dockerfile: infra/docker/web.Dockerfile
    environment:
      VITE_API_PROXY_TARGET: http://backend:8000
    ports:
      - "${WEB_EXPOSE_PORT:-5173}:5173"
    depends_on:
      - backend
    networks: [taxmind]

networks:
  taxmind:
    driver: bridge

volumes:
  mysql-data:
  redis-data:
  minio-data:
  etcd-data:
  milvus-data:
  neo4j-data:
  neo4j-logs:
```

落盘后必须执行 `docker compose config` 验证。若某镜像内没有 `curl`／`wget`，应使用镜像官方推荐的 healthcheck，不能简单删除健康检查。Compose 使用当前规范，不需要顶层 `version` 字段；相关行为参考 [Docker Compose Specification](https://docs.docker.com/compose/intro/compose-application-model/)。

### 11.18 `compose.override.yaml.example`

```yaml
services:
  backend:
    volumes:
      - ./apps/backend/src:/app/src:ro
    command: uv run uvicorn taxmind.entrypoints.api.main:create_app --factory --host 0.0.0.0 --port 8000 --reload

  web:
    volumes:
      - ./apps/web:/workspace/apps/web
      - web-node-modules:/workspace/apps/web/node_modules

volumes:
  web-node-modules:
```

开发者确需容器热更新时，将它复制为 `compose.override.yaml`。后端源码默认只读挂载；migration、导出契约等写操作在宿主机或显式命令中执行。

### 11.19 `infra/docker/backend.Dockerfile`

```dockerfile
FROM ghcr.io/astral-sh/uv:0.8.15 AS uv
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY apps/backend/src ./src
COPY apps/backend/migrations ./migrations
COPY apps/backend/alembic.ini ./alembic.ini
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "taxmind.entrypoints.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

本地模型建议使用单独 Worker 镜像 stage／extra，不能让 API 镜像无条件安装 torch。落盘时必须核对 uv 镜像 tag；首次通过后固定 digest。

### 11.20 `infra/docker/web.Dockerfile`

```dockerfile
FROM node:24-alpine

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable

WORKDIR /workspace
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile

COPY apps/web apps/web
COPY packages/contracts packages/contracts

EXPOSE 5173
CMD ["pnpm", "--filter", "@taxmind/web", "dev", "--host", "0.0.0.0"]
```

该文件用于开发 profile。生产前另建 multi-stage build，将 `dist` 放入受控静态服务器，不用 Vite dev server 对外服务。

### 11.21 `apps/backend/alembic.ini`

```ini
[alembic]
script_location = migrations
prepend_sys_path = src
version_path_separator = os
sqlalchemy.url = driver://unused

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

`migrations/env.py` 必须从 `get_settings()` 构造数据库 URL、导入全部 ORM metadata、支持 async engine，并在离线模式隐藏密码。禁止在 `alembic.ini` 写真实 DSN。

### 11.22 `.github/workflows/ci.yml`

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv sync --frozen --all-groups
      - run: uv run ruff check src tests
      - run: uv run ruff format --check src tests
      - run: uv run mypy src
      - run: uv run pytest -m 'not integration and not golden and not external_model' --cov

  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 11.14.0
      - uses: actions/setup-node@v4
        with:
          node-version: '24'
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint:web
      - run: pnpm typecheck:web
      - run: pnpm test:web
      - run: pnpm build:web

  contract:
    runs-on: ubuntu-latest
    needs: [backend, web]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - uses: astral-sh/setup-uv@v6
      - uses: pnpm/action-setup@v4
        with:
          version: 11.14.0
      - uses: actions/setup-node@v4
        with:
          node-version: '24'
          cache: pnpm
      - run: cd apps/backend && uv sync --frozen --all-groups
      - run: pnpm install --frozen-lockfile
      - run: bash scripts/export-openapi.sh
      - run: git diff --exit-code packages/contracts/openapi
      - run: bash scripts/generate-web-client.sh
      - run: pnpm typecheck:web
```

Integration／golden job 初期可手动触发，稳定后再设为 merge gate。真实模型密钥不得配置在普通 PR job。

### 11.23 `infra/neo4j/constraints.cypher`

```cypher
CREATE CONSTRAINT policy_document_id IF NOT EXISTS
FOR (n:PolicyDocument) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT clause_id IF NOT EXISTS
FOR (n:Clause) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT clause_source_chunk_id IF NOT EXISTS
FOR (n:Clause) REQUIRE n.source_chunk_id IS UNIQUE;

CREATE CONSTRAINT tax_type_code IF NOT EXISTS
FOR (n:TaxType) REQUIRE n.code IS UNIQUE;

CREATE CONSTRAINT business_action_code IF NOT EXISTS
FOR (n:BusinessAction) REQUIRE n.code IS UNIQUE;

CREATE CONSTRAINT subject_term_code IF NOT EXISTS
FOR (n:SubjectTerm) REQUIRE n.code IS UNIQUE;

CREATE CONSTRAINT region_code IF NOT EXISTS
FOR (n:Region) REQUIRE n.code IS UNIQUE;

CREATE INDEX policy_document_no IF NOT EXISTS
FOR (n:PolicyDocument) ON (n.doc_no);

CREATE INDEX policy_document_scope IF NOT EXISTS
FOR (n:PolicyDocument) ON (n.region_code, n.policy_status);
```

其他知识对象以稳定 MySQL ID 建唯一约束。关系的 `relation_id` 唯一性需要在 Neo4j 版本支持的约束能力范围内实现；若无法直接对关系建唯一约束，则通过 `MERGE` 模板和投影一致性检查保证，不能依赖“通常不会重复”。

### 11.24 `AGENTS.md`

```markdown
# TaxMind Pro Repository Rules

## Required checks

- Backend: `make lint`, `make typecheck`, `make test`.
- Frontend: generated API types must match the committed OpenAPI contract.
- Schema changes require an Alembic migration and a contract update.

## Architecture boundaries

- This is a modular monolith. Do not create a new service or database without an ADR.
- Domain code must not import FastAPI, SQLAlchemy, Redis, Milvus, Neo4j, MinIO, Celery, or model SDKs.
- API routers and Celery tasks are adapters; business rules belong in services/domain functions.
- Never write MySQL and Milvus/Neo4j in the same request transaction. Use the MySQL outbox.
- MySQL is the structured source of truth. Milvus and Neo4j projections must be rebuildable.
- Redis is never a source of truth for policy, facts, reviews, or final answers.

## Tax safety

- Never generate policy numbers, URLs, policy status, risk levels, or review status from free text.
- Every formal knowledge relation and key claim must have a source chunk.
- LLM output cannot alter deterministic rule hits or severity.
- Unreviewed chat, drafts, FAQ candidates, and graph relations must not enter published retrieval.
- Historical runs must keep their public/org knowledge snapshot and case profile version.
- Do not persist chain-of-thought.

## Security

- Every organization-owned repository method requires `org_id` from server-side TenantContext.
- Never accept raw Milvus filters or Cypher from an API client.
- Never log secrets, full client questions, original uploaded files, or unredacted sensitive data.
- Test cross-tenant reads and writes for every new organization-owned resource.

## Scope

- MVP uses synthetic or anonymized client facts only.
- Do not implement filing, payment, electronic tax bureau login, or official external tax opinions.
```

---

## 12. Script 文件契约

| 文件 | 入参 | 出参 | 失败规则 |
|---|---|---|---|
| `bootstrap.sh` | 可选 `--skip-infra` | 安装依赖、复制 `.env` 提示、启动基础设施、migration | 不覆盖已有 `.env`；任一步失败立即退出 |
| `wait-for-services.sh` | service list、timeout | 0／非 0 | 每服务独立报告；不得无限等待 |
| `export-openapi.sh` | 后端环境 | 更新 `taxmind-v1.openapi.json` | App 创建失败或 schema 非法即失败；不要求外部数据库连接 |
| `generate-web-client.sh` | OpenAPI path | generated TS types | 生成后执行 typecheck；禁止静默保留旧产物 |
| `verify-projections.sh` | snapshot code、可选 sample size | drift report／exit code | 默认只读；修复需另一个显式命令 |
| `seed-demo-data.sh` | fixture dir、target env | demo IDs | 只允许 development／test；检测非演示环境立即拒绝 |

Shell 脚本统一 `set -euo pipefail`，路径从仓库根解析，不假定当前工作目录。任何删除／重建命令必须打印精确目标并要求显式标志。

---

## 13. 初始 Migration 分批策略

Codex 不应一次生成一个上千行“全库 migration”。建议按依赖顺序拆分：

| Migration | 内容 | 依赖 |
|---|---|---|
| `0001_identity_audit` | organizations、users、members、auth_sessions、audit_logs | 无 |
| `0002_sources_documents` | source_sites、jobs、documents、versions、chunks、relations | identity actor FK 可空 |
| `0003_knowledge_governance` | controlled terms、objects/versions、relations、conditions、publish/snapshot/outbox/projection | documents |
| `0004_cases_conversations` | cases、profiles、facts、conversations、messages、summaries | identity |
| `0005_faq_procedure_risk` | FAQ versions/evidence/memory、procedure、risk rules/tests | documents/knowledge |
| `0006_runs_answers_reviews` | runs、routes、retrieval results、findings、drafts、claims/evidence、reviews、feedback | 上述全部 |
| `0007_seed_controlled_terms` | 最小税种／主体／地区／行为词表 | schema complete |

每个 migration 都必须有 downgrade 方案；对已发布知识和审计的破坏性 downgrade 只能在未承载数据的开发环境运行，文档中明确限制。

---

## 14. 健康检查与启动顺序

推荐顺序：

1. MySQL、Redis、MinIO、etcd；
2. Milvus、Neo4j；
3. MinIO bucket init、MySQL migration、Neo4j constraints、Milvus collection bootstrap；
4. API；
5. Worker、Scheduler；
6. Web；
7. Demo seed 和 smoke test。

### 14.1 API 健康端点

| Endpoint | 用途 | 内容 |
|---|---|---|
| `/health/live` | 容器存活 | 进程、event loop、build SHA；不探外部服务 |
| `/health/ready` | 是否接流量 | MySQL 必须 healthy；Redis／Milvus／Neo4j／MinIO 按功能降级策略给状态 |
| `/health/version` | 排障 | app version、commit SHA、contract version；不显示密钥／内部地址 |

`ready` 返回 `ready | degraded | not_ready`。MySQL 不可用必须 `not_ready`；Neo4j 不可用可以 degraded，但版本沿革路由需阻断或降级。

---

## 15. 日志、错误和请求上下文

### 15.1 RequestContext

每个 HTTP／task／workflow node 使用统一上下文：

| 字段 | 来源 |
|---|---|
| `request_id` | 客户端合法 ID 或服务端 UUIDv7 |
| `trace_id` | OpenTelemetry |
| `task_id` | Celery |
| `run_id` | analysis run，可空 |
| `org_id`、`user_id` | 已验证 Principal；日志可 hash／ID，不记机构名 |
| `knowledge_snapshot_ids` | 运行固定值 |

### 15.2 错误映射

- DomainError 由 API adapter 映射成既定错误码；domain 不 import HTTP status。
- Repository 唯一冲突映射 `RESOURCE_CONFLICT`，乐观锁映射 `RESOURCE_VERSION_CONFLICT`。
- SDK timeout 映射依赖错误并标 retryable；不得将原始 URI／token 放入 details。
- Celery task 将 DomainError 视为不可重试，TransientInfrastructureError 才按策略重试。

---

## 16. 脚手架生成任务拆分

建议 Codex 按以下顺序提交，避免一次创建数百个空文件后难以验证：

### Task 1：仓库与工具链

- 顶层文件、pnpm workspace、后端 pyproject、Web package、Git hooks、CI；
- 验收：`uv lock`、`pnpm install`、最小 lint／typecheck 成功。

### Task 2：Backend Bootstrap

- Settings、logging、container、FastAPI factory、错误包络、request ID、health；
- 验收：无数据库时 liveness 成功，ready 正确失败／降级，OpenAPI 可导出。

### Task 3：Infrastructure Adapters

- Compose、MySQL Session/UoW、Redis、MinIO、Milvus、Neo4j clients；
- 验收：health、连接释放、timeout、日志脱敏。

### Task 4：Identity／Cases／Conversation

- 首批 migration、租户、RBAC、事项画像、消息和短记忆；
- 验收：跨租户负测、事实确认版本、Redis 恢复。

### Task 5：Knowledge Offline

- Sources、Documents、Knowledge、FAQ、Procedure、Risk 管理骨架和 Outbox；
- 验收：手工文件导入→解析→候选→审核→发布→投影。

### Task 6：Online GraphRAG

- Retrieval、Orchestration、Generation、Review；
- 验收：七路由、SSE、追问 resume、规则、引用、审核包。

### Task 7：Web P0

- 登录、事项、对话、证据、政策、风险、办税、审核、知识后台；
- 验收：P0 E2E 和权限状态。

---

## 17. 脚手架验收清单

### 17.1 目录和依赖

- [ ] API、Worker、Scheduler 来自同一个 `apps/backend` 包和镜像。
- [ ] Domain 文件没有 import 框架／存储 SDK。
- [ ] Router／Task 中没有业务规则、SQL、提示词。
- [ ] 模块间没有 import 对方 ORM model。
- [ ] 生成类型和 OpenAPI／JSON Schema 可重复生成。

### 17.2 配置和安全

- [ ] `.env.example` 与 Settings 字段一致，仓库无真实 secret。
- [ ] `uv.lock`、`pnpm-lock.yaml` 可在干净环境复现。
- [ ] Compose healthcheck 和 volumes 完整，`docker compose config` 通过。
- [ ] API／Worker 使用非 root 用户镜像。
- [ ] JWT、DSN、DashScope key、客户问题不会进入日志。

### 17.3 功能骨架

- [ ] `/health/live`、`/health/ready`、统一错误包络和 request ID 可用。
- [ ] 租户上下文不可由请求 body／query 任意指定。
- [ ] MySQL UoW 可把业务变更和 Outbox 同事务提交。
- [ ] Redis checkpoint 有 TTL 和版本；MySQL 可恢复持久状态。
- [ ] Milvus／Neo4j adapter 只接受 typed filters／白名单模板。
- [ ] SSE 使用 Bearer fetch 流，不把 token 放 URL。

### 17.4 质量门禁

- [ ] `make lint`、`make typecheck`、`make test` 通过。
- [ ] 后端 coverage 初始门槛 ≥80%，domain／rule／tenant 核心逻辑不允许用覆盖率豁免。
- [ ] 前端 build、typecheck、unit test 通过。
- [ ] 跨租户读写负向测试通过。
- [ ] OpenAPI 导出后 Git 无未提交 drift。
- [ ] 所有脚本在错误条件下非零退出，不假装成功。

---

## 18. 明确暂不创建的目录／文件

为避免脚手架空洞膨胀，MVP 不创建：

- `microservices/`、`service-mesh/`、`k8s/`、Helm；
- 通用 `agents/`、`multi_agent/`；当前是受控工作流，不是多智能体产品；
- Elasticsearch／OpenSearch adapter；
- GraphQL、WebSocket gateway；
- 真实税务局接口、自动申报／缴税客户端；
- 通用低代码规则设计器；
- 未确定云厂商的 Terraform；
- 大而全的 `utils.py`、`common.py`、`helpers.py`；共享代码必须有明确领域含义。

---

## 19. 进入代码生成前仍需确认的五项参数

这些参数不会改变目录结构，但会改变实际 lockfile／镜像和模型配置：

1. DashScope 使用的具体 LLM 型号及上下文／价格预算；
2. BGE-M3 和 reranker 是本机加载、独立推理服务，还是云端接口；
3. 开发机是否需要完整启动 Milvus／Neo4j，还是允许通过 Compose profile 按需开启；
4. 首批演示数据规模以及是否有税务师审核资源；
5. MVP 只用于个人面试展示，还是会进入机构封闭试点。

如果暂不确认，Codex 应使用 adapter fake 完成单元测试，以本地 Compose 完成集成测试，不得把供应商调用写死在领域代码中。

---

## 附录 A：文件命名规则

| 类型 | 命名 |
|---|---|
| Python module／function | `snake_case` |
| Python class／Pydantic schema | `PascalCase` |
| React component／page | `PascalCase.tsx` |
| React hook | `use-*.ts` 或项目统一 `useX.ts`，本项目树采用 kebab 文件名 |
| API path | 小写复数资源，kebab-case；`/risk-rule-versions/{id}` |
| Event／task | `domain.action.v1`；如 `projection.faq.v1` |
| DB table／column | `snake_case` |
| Environment | `UPPER_SNAKE_CASE` |
| Permission | `resource:action`；如 `knowledge:publish` |

## 附录 B：首次脚手架完成后的最小演示

脚手架不是以“目录都存在”为完成标准。首次可运行演示必须完成：

1. `make infra-up` 启动五类存储及 Milvus 的 etcd 依赖；
2. `make migrate` 建立最小 identity／case 表；
3. API 返回 health、request ID 和统一错误包络；
4. Web 登录占位页调用 health，并能显示结构化错误；
5. 创建两个测试机构，跨租户读取返回统一 404；
6. 创建一条 run，SSE 推送 `run.started → facts.required`；
7. 断开后携带 Last-Event-ID 重连；
8. Outbox 插入一条测试事件，Worker 幂等消费并写 projection sync state；
9. CI 的 backend、web、contract 三个 job 全部通过。

完成这九项后，再进入政策导入和 GraphRAG 业务实现。
