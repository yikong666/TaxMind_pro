# Changelog

## 2026-08-31 - Stage 5.7 Celery Outbox 调度基线

- 新增 Celery Worker 与 Beat 配置，Redis 使用独立 broker/result database；任务仅接受 JSON，禁用 pickle，启用确认后消费与单任务预取。
- 新增 `taxmind.outbox.dispatch.v1` 维护任务和保守的 60 秒默认调度；任务调用既有 Outbox 服务，投影执行端未配置时仍只进入受控重试。
- 新增 `make worker` 与 `make scheduler` 本地入口；尚未加入容器化 Worker，也未接入真实 Milvus/Neo4j Adapter 或快照激活。

影响模块：Backend Worker、Celery、Redis Queue、Outbox、Settings、Local Development Commands。

迁移与回滚：无数据库迁移。回滚应用和依赖锁文件即可停止 Beat 调度；已有 Outbox 事件仍保留在 MySQL，且不会被 API 直接投影。

## 2026-08-31 - Stage 5.6 Outbox 受控消费与投影状态

- 新增 Worker 可调用的 Outbox 消费服务：以 MySQL 行锁领取 `pending` / `retryable` 投影事件，再以独立事务记录完成、可重试或死信结果。
- 新增 `projection_sync_states` 幂等状态写入；成功、失败和重试不会通过 API 直接双写 Milvus 或 Neo4j。
- 失败只记录稳定安全错误码；默认执行端为未配置状态，会进入受控重试而不会虚报外部投影已完成。超过配置的尝试次数后事件进入 `dead`。
- 新增批量大小、最大尝试次数和重试延迟配置，并提供 Worker 侧服务工厂；尚未接入 Celery 调度及真实 Milvus/Neo4j Adapter。

影响模块：Backend Knowledge Outbox、Projection Sync State、Worker Entry Point、Settings、MySQL Integration Tests。

迁移与回滚：复用 Alembic `20260831_0006` 的 Outbox 与投影状态表；回滚应用会停止新的消费逻辑，不会删除已记录的处理结果或死信状态。

## 2026-08-31 - Stage 5.5 知识快照草稿与投影 Outbox

- 仅允许已验证通过的发布批次物化为 `pending_activation` 公共知识快照；快照保留批次摘要和候选来源校验和，尚未激活。
- 创建快照及条目后，在同一 MySQL 事务写入两条待处理 Outbox 事件：政策检索投影与图谱投影请求；API 不直接写入 Milvus 或 Neo4j。
- 新增快照物化 API 与审核审计事件；响应明确返回待处理投影事件数量，不把快照误标为已上线。

影响模块：Backend Knowledge Snapshot、Outbox、Audit、API Contracts、MySQL Integration Tests。

迁移与回滚：复用 Alembic `20260831_0006` 的知识快照、条目与 Outbox 表；回滚应用会停止新快照物化，不会自动删除已生成的待激活快照或 Outbox 事件。

## 2026-08-31 - Stage 5.4 知识候选人工审核与发布验证门禁

- 新增候选人工审核：仅 `knowledge:review` 可决定 `approved` 或 `rejected`，驳回必须填写安全原因；候选抽取者不得审核自己的候选。
- 审核结果保存审核人和审核时间，并记录 `knowledge.candidate.reviewed` 审计事件；候选不会因审核通过自动进入正式检索。
- 新增待验证发布批次：仅已审核通过的候选可被纳入不可变 checksum 清单，批次初始状态为 `pending_validation`。
- 新增发布批次验证：校验候选数、审核状态、来源条款与清单摘要，结果为 `validated` 或 `validation_failed`，不创建快照、不写 Outbox、不投影到 Milvus/Neo4j。
- 新增 Alembic `20260831_0007`，为候选增加审核人和审核时间追溯字段。

影响模块：Backend Knowledge Review、Knowledge Candidate、Audit、API Contracts、MySQL Integration Tests。

迁移与回滚：升级至 Alembic `20260831_0007`；降级只移除候选审核人/时间字段，执行前应确认没有需要保留的审核追溯数据。发布批次和候选主数据仍由 `20260831_0006` 管理。

## 2026-08-31 - Stage 5.3 知识候选抽取与审核前队列

- 新增对已解析 `draft` 资料版本的确定性候选抽取：每条可引用条款生成一条 `policy_clause` 候选，并以相同资料版本和抽取器版本保证幂等。
- 每个候选强制保留来源资料、来源条款、原文摘要、地区、有效期、抽取方法、置信度与 `pending_review` 状态；候选仅进入审核前队列，不会成为正式检索依据。
- 新增候选批次创建与待审核队列 API；候选批次不接收模型、Prompt、发布或投影输入，当前实现也不会调用外部模型。
- 已拒绝已发布、未解析或非草稿资料进入候选抽取；创建过程写入 `knowledge.candidate_batch.created` 审计事件。

影响模块：Backend Knowledge Candidates、Documents Read Model、Audit、API Contracts、MySQL Integration Tests。

迁移与回滚：复用 Alembic `20260831_0006` 的候选批次与候选表；回滚应用会停止候选生成与队列读取，但不会将未审核候选发布或写入检索投影。

## 2026-08-31 - Stage 5.2 手工资料导入与确定性解析

- 新增 `POST /api/v1/knowledge/uploads`：接收来源、资料元数据和受控文件，创建可幂等回查的导入任务；新增 `GET /api/v1/knowledge/jobs/{job_id}`。
- 原件以内容 SHA-256 写入私有 MinIO `taxmind-raw`；同对象键仅允许相同内容复用，冲突内容会被拒绝覆盖。
- 支持 UTF-8 纯文本、HTML 和带文本层的 PDF；HTML 忽略脚本/样式内容，解析结果按法条边界或段落生成资料草稿条款。
- 成功导入只创建 `draft` 资料、版本和条款；对象存储或解析失败会把任务标为 `failed` 并写入安全错误码，不会发布正式知识。
- 新增 `minio`、`pypdf` 与 `python-multipart` 依赖；未接入网页采集、Celery、模型调用、审核发布、Milvus 或 Neo4j 投影。

影响模块：Backend Sources、Documents、MinIO Adapter、API Contracts、MySQL/MinIO Integration Tests。

迁移与回滚：复用 Alembic `20260831_0006` 的导入任务与资料表；回滚应用后不会删除已留存原件，需由知识管理员按审计记录确认后单独处理。

## 2026-08-31 - Stage 5.1 离线知识治理契约与数据模型

- 新增官方公开来源登记与列表 API；来源默认进入 `draft`，仅登记白名单配置，不会自动采集。
- 来源地址仅接受无凭据、无查询参数的 HTTPS 官方站点；白名单规则拒绝 Cookie、Token、密码和密钥字段，低频检查间隔不得少于 60 分钟。
- 新增采集任务、候选批次、知识候选、发布批次、知识快照、Outbox 与投影同步状态的 MySQL 主数据契约。
- 知识候选强制关联来源资料与条款；Milvus、Neo4j 继续作为后续可重建投影，不在 API 事务中双写。
- 本步未实现文件解析、网页采集、模型抽取、人工审核执行或向量/图谱写入，也未调用外部模型。

影响模块：Backend Sources、Knowledge Contracts、Audit、API Contracts、MySQL Migration。

迁移与回滚：升级至 Alembic `20260831_0006`；降级会删除本步新增的来源与知识治理契约表，只能在确认没有需保留数据时执行。

## 2026-08-31 - Stage 4.7 会话、消息与短期记忆

- 新增事项内会话创建、幂等用户消息写入、消息分页读取和上下文读取 API。
- 新增 MySQL 会话、消息和摘要表；消息正文先持久化 MySQL，不保存模型隐藏推理。
- 新增带机构隔离键和可配置 TTL 的 Redis 短期记忆；缓存缺失或不可用时从 MySQL、当前画像和已确认事实重建。
- 新增事项工作台会话抽屉，明确标识当前阶段尚未接入模型回答，并提供虚构预览消息流。
- 新增 `redis` 官方 Python 客户端依赖和短期记忆配置项。

影响模块：Backend Conversations、Cases、Audit、Redis Adapter、API Contracts、Web Cases Workspace。

迁移与回滚：升级至 Alembic `20260831_0005`；降级会删除会话、消息和摘要表，只能在确认没有需保留会话数据时执行。

阶段验收：补充跨机构会话访问、消息幂等和真实 MySQL/Redis 事务链路回归；虚构测试数据在事务内回滚，Redis 缓存缺失时可由 MySQL 当前画像、已确认事实和最近消息恢复。

## 2026-08-31 - Stage 4.4 登录与政策检索前端

- 新增内存会话登录页和政策检索页；访问令牌不写入浏览器持久化存储。
- 新增无需账号的虚构数据预览模式，不访问后端、模型或真实政策资料。
- 政策检索使用共享 OpenAPI 契约类型，并展示已发布状态、来源机关、版本、可引用条款、有效期与全国口径回退提示。
- 补充登录界面、检索请求和 Ant Design 响应式测试环境覆盖；浏览器实测待本地端口监听权限恢复后执行。

## 2026-08-31 - Stage 4.5 事项工作台前端

- 新增事项列表、匿名化事项创建和画像详情抽屉；正式模式调用既有事项接口，预览模式仅展示虚构事项。
- 事项创建默认携带 `synthetic` 数据分类，不提供真实客户资料录入路径。

## 2026-08-31 - Stage 4.6 事实确认与画像换版

- 新增事项事实候选确认/拒绝接口；所有候选必须有且仅有一个人工决定，并校验画像版本冲突。
- 确认或拒绝后生成新的不可变画像版本，复制仍有效的已确认事实，并在新版本中保留拒绝候选状态。
- 新增事项画像事实确认抽屉；预览模式使用虚构数据演示换版，正式模式通过共享 OpenAPI 契约调用后端。
- 事实来源区分用户输入与审核人决定，并记录 `case.facts.confirmed` 审计事件。

影响模块：Backend Cases、Audit、API Contracts、Web Cases Workspace。

迁移与回滚：本步复用现有事项、画像和事实表，不新增数据库迁移；回滚应用与契约改动即可。

## 2026-08-30 - Stage 4.3 知识资料版本与受控发布底座

- 新增官方资料、不可变版本和可引用条款的 MySQL 主数据迁移；资料正文只在版本/条款草稿中保存，未审核版本不会成为当前检索依据。
- 新增知识资料草稿、条款录入、提交审核、非创建者发布和按地区/业务日期精确检索接口；检索仅返回已发布且有效的资料条款，全国资料回退会显式标记 `national_only`。
- 后续模型调用固定从 `DASHSCOPE_API_KEY` 环境变量读取密钥，模型配置只允许 `qwen-max` 或 `qwen3-max`；本阶段未调用外部模型、未采集网站或导入真实资料。

## 2026-08-30

### 产品文档基线（未发布）

- 归档 MVP 产品需求与功能规格说明书（PRD），并修正文档索引与仓库 README 入口。
- 后续业务模块以 PRD 定义的范围、验收指标和排除项为准。

### 工程基座（未发布）

- 初始化 TaxMind Pro Monorepo 工具链和文档目录。
- 增加 FastAPI 应用工厂、运行日志、统一错误、请求 ID 和健康检查基线。
- 增加 React 工作台最小应用壳、健康状态和内部专业辅助提示。
- 增加 OpenAPI 导出、前端类型生成、单元测试、契约测试和 CI 基线。

### 本地基础设施与迁移底座（未发布）

- 新增 Compose 开发基础设施：MySQL、Redis、MinIO、Milvus、Neo4j。
- 新增 SQLAlchemy async、Alembic 与 asyncmy，以及 Identity/Tenant、审计日志的初始迁移。
- 修正 Milvus 2.6 Standalone 的消息与对象存储启动配置，避免使用已不支持的 `minio` 存储类型。
- 尚未接入真实登录、业务 API、客户数据或外部模型服务。

影响模块：仓库基础设施、Backend Bootstrap、Web Bootstrap、Contracts。

迁移与回滚：不包含数据库迁移或业务数据；删除本批新增文件即可回滚，现有 `AGENTS.md` 未被覆盖。

验证结果：以本轮实际检查结果为准，完成后补充到任务交付记录。

### 身份认证与机构权限最小闭环（未发布）

- 新增 Argon2 口令哈希、JWT 访问令牌、刷新令牌轮换与可撤销会话。
- 新增开发环境一次性管理员初始化、登录、刷新、登出、当前用户和机构成员管理 API。
- 新增机构范围校验、角色权限校验、成员乐观锁和保留至少一名激活机构管理员的保护。
- 新增 `auth_sessions` 表，并为 `organization_members` 增加 `version_no`。

影响模块：Backend Identity、Audit、API、MySQL Migration。

迁移与回滚：升级至 Alembic `20260830_0002`；降级会移除 `auth_sessions` 和成员版本列，仅可在确认无依赖会话数据时执行。

验证结果：后端单元/契约测试、静态检查和本地 Docker MySQL 的认证端到端回归均已执行。

### 事项、画像与事实快照最小闭环（未发布）

- 新增事项创建、列表、详情与画像新版本 API，并按机构范围和角色权限控制访问。
- 新增不可变主体画像版本和随版本固化的事实快照；过期的前序版本提交返回乐观锁冲突。
- 限制事项输入为虚构或匿名化数据，并拒绝常见手机号、身份证号和统一社会信用代码模式。
- 完善访问令牌拒绝的安全原因日志，不记录令牌、口令或客户输入。

影响模块：Backend Cases、Identity、Audit、API、MySQL Migration。

迁移与回滚：升级至 Alembic `20260830_0003`；降级会移除事项、画像与事实快照表，仅可在确认无依赖事项数据时执行。

验证结果：后端单元/契约测试、静态检查及本地 Docker MySQL 的认证和事项端到端回归均已执行。
