# TaxMind Pro 技术开发设计说明书（MVP）

> 文档用途：作为 Codex 后续生成项目目录、基础配置、数据库迁移、后端服务、前端页面与测试用例的直接开发依据。  
> 文档版本：v1.0-draft  
> 设计基线：`TaxMind-Pro-MVP-PRD.md`、`taxmind-pro-system-architecture.html`  
> 本轮边界：只定义模块、数据、接口、算法、状态、约束和验收要求；不生成项目目录与实现代码。

---

## 0. 结论与决策状态

### 0.1 系统定位

TaxMind Pro 是面向税务师事务所、代理记账公司和财税咨询机构的内部专业辅助系统。系统以官方政策条款为证据，以确定性条件／风险规则为判断骨架，以 GraphRAG 和大模型完成问题理解、关联检索、解释与草稿生成；任何正式结论必须由专业人员审核。

### 0.2 本版已确定

| 决策 | 结论 |
|---|---|
| 直接用户 | 财税专业机构中的顾问、税务师、复核人、知识管理员和机构管理员 |
| 被服务客户 | 小规模纳税人、小型微利企业、个体工商户；不是系统账号用户 |
| 地域 | 全国有效政策＋广东省地方政策＋深圳市办税口径 |
| 业务范围 | 增值税小规模常见事项、小型微利企业所得税条件、个体工商户经营所得、常见发票、申报、优惠、8—12 个办税事项、事项级风险审查 |
| 数据边界 | 只使用公开政策与虚构、脱敏或匿名化事项事实；不接入真实账簿、全量发票、申报表和电子税务局 |
| 主数据归属 | MySQL 保存结构化事实、版本、状态与治理记录；MinIO 保存原始文件与大对象；Milvus、Neo4j 为可重建的检索投影；Redis 只保存短期状态和缓存 |
| 在线协议 | REST JSON 承载命令与查询；SSE 承载单向运行进度和回答增量；MVP 不使用 WebSocket |
| 检索 | MySQL 精确元数据过滤＋Milvus 稠密／BM25 稀疏混合召回＋Neo4j 受控关系扩展＋FAQ 检索＋确定性规则 |
| 风险判断 | 规则引擎决定命中和风险等级；LLM 不得新增、删除或改写规则命中 |
| 知识发布 | 抽取结果、FAQ、规则、办税事项均需审核发布；未审核资产不能进入正式检索 |
| 结果边界 | 输出为“内部分析和客户答复草稿”，默认 `待审核`，不构成正式税务意见 |

### 0.3 建议但可在实施前替换

| 项目 | 本文建议 | 可替换边界 |
|---|---|---|
| 后端／前端 | FastAPI；React＋TypeScript | 不影响本文 API 和状态约束即可替换 |
| 工作流 | LangGraph | 必须保留可持久化状态、暂停追问、恢复、人工介入能力 |
| 异步任务 | Celery＋Redis | 可替换为其他可靠队列，但不得依赖 Web 进程内后台任务完成知识发布 |
| 嵌入／重排 | BGE-M3（1024 维）＋bge-reranker-v2-m3 | 更换模型必须新建索引版本并跑回归集 |
| 生成模型 | DashScope 中可配置的大模型 | 模型名、参数、提示词版本必须随运行留档 |
| 部署 | Docker Compose 单机／单节点 MVP | 生产试点前再评估 Kubernetes、高可用和灾备 |

### 0.4 实施前待确认，但不阻塞文档

1. MVP 是作品集演示还是会进入一家机构的封闭试点；本文按“可试点前验证”的安全标准设计。
2. 是否有税务师承担知识、规则和金标准的最终审核；若没有，系统只能验收工程闭环，不能宣称税务正确性。
3. 首批种子规模；本文建议 150—300 份政策／指引、30—50 条风险规则、80—150 条审核 FAQ、8—12 个办税事项、200—300 道金标准问题。

---

## 1. 设计目标与非目标

### 1.1 开发目标

1. 同一份政策的原件、版本、条款、向量片段、图关系和答案引用通过统一 ID 对齐。
2. 在生成前完成政策状态、业务日期、地区、主体和审核状态硬过滤。
3. 一次复杂咨询可拆成多个路由和子任务，分别获得证据和判断后再合成草稿。
4. 每个关键主张可回放到：事项事实版本、检索候选、政策条款、规则版本、提示词／模型版本和审核动作。
5. FAQ、机构经验和会话记忆相互隔离；普通聊天不能自动成为知识。
6. 任一衍生存储损坏时可由主数据重建，避免跨数据库双写不一致。
7. 可以建立稳定的离线评测和发布门禁，而不是只凭演示效果判断质量。

### 1.2 非目标

- 不自动申报、缴税、登录电子税务局或代表机构对外出具正式意见。
- 不建设全中国税法、全行业、全地区知识库。
- 不接入真实企业非公开涉税数据，不做基于账簿／发票明细的全量税务体检。
- 不让 LLM 自行解释为规则命中，也不把生成内容自动写回正式知识。
- 不在 MVP 同时引入 Elasticsearch／OpenSearch；Milvus 的稠密向量和 BM25 稀疏检索已覆盖当前混合召回需求。
- 不建设通用低代码规则平台、复杂 BPM 引擎、微服务集群或 Kubernetes。

---

## 2. 总体技术原则

### 2.1 单一事实源与可重建投影

| 数据类别 | 事实源 | 投影／缓存 | 说明 |
|---|---|---|---|
| 机构、用户、事项、事实、消息、审核 | MySQL | Redis | Redis 丢失后从 MySQL 恢复 |
| 文档元数据、政策状态、条款文本、知识关系台账 | MySQL | Milvus、Neo4j | 发布事件驱动索引和图投影 |
| 原始 HTML／PDF／图片、OCR 和解析快照 | MinIO | 无 | MySQL 只保存对象键、哈希和状态 |
| 政策条款向量、FAQ 问题向量、审核案例向量 | MySQL 中的已发布内容 | Milvus | Milvus 不承载审核状态真相 |
| 图拓扑和多跳查询 | MySQL 中的已发布关系台账 | Neo4j | Neo4j 是在线图查询服务，不是不可替代的唯一副本 |
| 当前对话工作记忆、运行检查点、热点缓存 | MySQL 中的持久结果 | Redis | 有 TTL，不可作为政策或审核依据 |

此前架构图中“Neo4j 是领域关系权威库”在实施上应解释为：**Neo4j 是已发布图关系的在线查询权威；关系的来源、审核、版本和重建台账仍由 MySQL 管理。** 这样可消除双主和分布式事务问题。

### 2.2 写入规则

1. 业务请求先在 MySQL 事务内写主记录和 `outbox_events`。
2. 异步消费者读取 Outbox，幂等写入 Milvus／Neo4j 或处理 MinIO 文件。
3. 消费成功回写同步状态；失败重试，不回滚已提交的主业务事务。
4. 查询必须同时检查投影中的 `review_status`、`policy_status`、`version_id`，并以 MySQL 当前发布状态做最终复核。
5. 禁止 API 层直接跨 MySQL、Milvus、Neo4j 做“尽力双写”。

### 2.3 标识、时间和版本约定

| 项目 | 规范 |
|---|---|
| 主键 | 应用生成 UUIDv7，API 使用字符串；MySQL 暂用 `CHAR(36)`，后续可无损迁移 `BINARY(16)` |
| 时间 | 数据库存 UTC `DATETIME(3)`；API 用 ISO 8601 UTC，如 `2026-08-29T10:15:00.123Z` |
| 地区 | GB/T 2260 行政区划码；全国用 `CN`，广东 `440000`，深圳 `440300` |
| 金额 | `DECIMAL(18,2)`＋币种，不使用浮点数 |
| 状态 | `VARCHAR(32)`＋应用枚举／检查约束，不用 MySQL `ENUM`，便于迁移和扩展 |
| 乐观锁 | 可编辑聚合根使用 `version_no INT`；更新 API 必传 `If-Match` 或 `version_no` |
| 软删除 | 正式业务和知识对象使用 `status=retired/archived`；审计记录不可软删或物理删 |
| JSON | 只存扩展属性、规则表达式和运行快照；高频过滤字段必须拆为列 |
| 多租户 | 所有机构业务表必须有 `org_id`，所有仓储查询强制注入 `org_id`；公共政策表 `org_id` 为空且不可被机构直接修改 |

### 2.4 统一生命周期

知识资产（政策版本、关系、FAQ、规则、办税事项）使用：

`draft → pending_review → approved → published → retired`

- `approved` 表示内容已审核，但尚未进入稳定检索快照。
- `published` 表示已进入指定 `knowledge_snapshot`，可被线上运行使用。
- 修改已发布资产必须产生新版本，不得原地覆盖。
- `rejected` 是审核结果，不是可继续编辑的正式状态；退回后创建或恢复 draft 版本。

业务事项使用：

`draft → analyzing → pending_review → returned → approved → archived`

---

## 3. 组件选型与必要性

| 组件 | MVP | 解决的问题 | 取舍与限制 |
|---|---|---|---|
| React＋TypeScript | 保留 | 事项工作台、证据并排阅读、审核交互、流式状态 | 不做微前端 |
| FastAPI | 保留 | 类型化 REST、OpenAPI、异步 I/O、SSE | 业务逻辑不得写在路由函数内 |
| MySQL 8 | 必须 | 事务、版本、审核、精确条件、主数据和审计 | 不承担语义召回，不保存文件二进制 |
| Milvus | 必须 | 稠密向量、BM25 稀疏向量和混合召回 | 仅为索引，可整库重建；不再叠加 ES |
| Neo4j | 必须但限定 | 政策沿革、条件／义务／证据的受控多跳查询 | 精确文号搜索和简单 FAQ 不走图谱 |
| Redis | 保留 | 会话短记忆、LangGraph 检查点、缓存、分布式锁、Celery broker | 不存长期事实；不同用途使用 key 前缀／逻辑 DB |
| MinIO | 保留 | 原始 HTML／PDF、附件、OCR、解析快照、导出件 | 只有对象键进入数据库；开启版本／生命周期策略 |
| LangGraph | 建议保留 | 多步路由、追问暂停、恢复、人工介入和状态回放 | 简单政策详情接口不强行走图 |
| Celery | 建议新增 | 采集、OCR、解析、嵌入、图同步、评测等可靠异步任务 | 任务必须幂等；MVP 不拆独立微服务 |
| BGE-M3 | 保留 | 中文与多语稠密嵌入，统一 1024 维基线 | 模型升级建新 collection，不原地混向量 |
| bge-reranker-v2-m3 | 保留 | 对混合召回候选做语义重排 | 只重排前 20—40 条，控制延迟 |
| DashScope LLM | 保留且可配置 | 事实抽取、路由补充、问题拆解、解释和草稿生成 | 不负责政策状态硬判断和风险命中 |
| SSE | 必须 | 服务端向浏览器推送分析阶段和答案增量 | MVP 是单向流，无需 WebSocket 的双向连接复杂度 |
| OCR | 条件启用 | 处理官方扫描 PDF／图片 | 仅检测为扫描件时运行，文本型 PDF 不走 OCR |
| Docker Compose | 保留 | 本地和演示环境的一致部署 | 生产 SLA 不以此方案承诺 |
| RAGAS | 辅助 | 生成／检索指标的补充计算 | 不能替代税务金标准、规则回归和引用核验 |

选型依据：Milvus 官方文档已支持基于 BM25 的全文检索和多向量混合搜索，因此 MVP 无需再维护一套 Elasticsearch；FastAPI 官方支持 SSE；LangGraph 的 checkpointer 用于线程级状态持久化，store 用于跨线程长期记忆，并支持 interrupt／resume 的人工介入。实现时分别参考 [Milvus 全文检索](https://milvus.io/docs/full-text-search.md)、[Milvus 多向量混合检索](https://milvus.io/docs/multi-vector-search.md)、[FastAPI SSE](https://fastapi.tiangolo.com/tutorial/server-sent-events/)、[LangGraph 持久化](https://docs.langchain.com/oss/python/langgraph/persistence) 和 [LangGraph Interrupt](https://docs.langchain.com/oss/python/langgraph/interrupts)。

---

## 4. 运行架构与模块边界

### 4.1 部署单元

MVP 采用“模块化单体＋异步 Worker”，不拆微服务：

| 部署单元 | 内部模块 | 可访问存储 |
|---|---|---|
| Web App | 对话、事项、政策、FAQ、风险、办税、审核、知识后台 | 只调用 API |
| API App | 身份与租户、事项、查询运行、检索编排、生成、审核、知识管理 | MySQL、Redis；通过适配器只读 Milvus／Neo4j／MinIO |
| Worker | 采集、解析、OCR、嵌入、图同步、快照发布、评测 | MySQL、Redis、MinIO、Milvus、Neo4j |
| Scheduler | 白名单增量检查、过期任务、索引一致性、定时评测 | 通过队列派发 Worker |
| Model Gateway | 嵌入、重排、LLM 的统一超时、重试、配额、日志脱敏 | 外部／本地模型服务 |

### 4.2 业务模块

| 模块 | 核心职责 | 禁止承担 |
|---|---|---|
| Identity & Tenant | 登录、机构成员、RBAC、租户上下文 | 不直接拼接任意 SQL 租户条件 |
| Case Workspace | 事项、主体画像、事实版本、状态 | 不把客户画像写入公共知识图谱 |
| Conversation & Memory | 消息持久化、摘要、短期状态、已确认事实装载 | 不将未审核模型输出沉淀为 FAQ |
| Source Ingestion | 白名单来源、抓取／导入任务、去重、版本发现 | 不绕过登录、验证码或反爬措施 |
| Document Processing | 格式识别、清洗、结构解析、父子分块、异常记录 | 不直接发布知识 |
| Knowledge Governance | 候选实体／关系、标准化、审核、快照和影响分析 | 不让低置信抽取进入正式图谱 |
| FAQ Knowledge | 官方 FAQ、机构审核 FAQ、问题变体、证据绑定、发布 | FAQ 不能替代正式条款核验 |
| Procedure Knowledge | 地区化办税事项、步骤、材料、渠道、期限、依据 | 不模拟电子税务局操作 |
| Risk Rule | 规则 DSL、版本、测试、执行、命中解释 | LLM 不得改变命中和等级 |
| Query Orchestrator | 范围闸门、事实抽取、七类路由、检索计划、暂停／恢复 | 不直接实现底层数据库查询 |
| Retrieval | 精确、稠密、BM25、FAQ、图谱、规则检索与重排 | 不生成最终结论 |
| Evidence Fusion | 去重、父块回填、来源分级、冲突与缺口识别 | 不隐藏冲突 |
| Generation & Validation | 结构化分析、草稿、引用核验、可信维度、责任声明 | 不输出内部思维链，不编造文号 |
| Review & Feedback | 审核包、逐结论决策、退回、纠错、发布闭环 | 普通顾问不能直接发布公共知识 |
| Audit & Observability | 请求链路、模型／提示词版本、成本、错误、敏感字段脱敏 | 不记录模型私有推理过程 |

### 4.3 主流程

1. 官方资料进入 MinIO，MySQL 建立来源、文档和版本记录。
2. Worker 解析为条款／父子块并写 MySQL，生成知识候选、FAQ 候选和办税事项候选。
3. 知识管理员审核并创建发布快照；Outbox 将条款索引投影到 Milvus、关系投影到 Neo4j。
4. 顾问创建事项并确认最小主体事实；原始消息和确认事实写 MySQL，当前运行状态写 Redis。
5. Query Orchestrator 执行范围闸门和七类业务路由；缺事实时通过 LangGraph interrupt 暂停并追问。
6. Retrieval 按路由并行调用 MySQL／Milvus／Neo4j／FAQ／规则，Evidence Fusion 形成可追溯证据包。
7. 规则引擎先产生适用性／风险判断，LLM 再解释并生成草稿；引用校验失败则降级、追问或转人工。
8. 结果保存为待审核版本，通过 SSE 返回；审核动作、反馈和知识修订形成闭环。

### 4.4 十二项产品功能到开发模块的映射

| 产品功能 | 主要前端入口 | 后端主模块 | 是否进入对话流 |
|---|---|---|---|
| FR-01 机构与角色 | 机构设置 | Identity & Tenant | 否，只提供权限上下文 |
| FR-02 事项工作台与画像 | 事项列表／详情 | Case Workspace | 画像摘要常驻对话侧栏 |
| FR-03 智能问询与范围闸门 | 对话输入／追问卡 | Query Orchestrator | 是，作为对话入口 |
| FR-04 政策检索 | 独立检索页＋对话证据卡 | Retrieval | 是，可由问题自动触发 |
| FR-05 政策证据与沿革 | 证据抽屉／政策详情 | Evidence Fusion＋Knowledge | 是，以证据卡展开；详情独立页 |
| FR-06 政策适用性 | 条件矩阵卡 | Rule／Condition Engine | 是，缺事实时插入追问 |
| FR-07 咨询辅助与草稿 | 对话结果＋草稿编辑器 | Generation & Validation | 是，草稿编辑可在右侧工作区 |
| FR-08 事项风险审查 | 风险卡＋独立风险页 | Risk Rule | 是，可作为复合路由子任务 |
| FR-09 办税事项指导 | 办税卡＋事项库 | Procedure Knowledge | 是，可在对话中召回完整事项卡 |
| FR-10 人工审核 | 审核队列／审核详情 | Review | 否；接收对话运行形成的审核包 |
| FR-11 知识运营 | 知识后台、FAQ、规则、发布 | Ingestion／Knowledge Governance | 否；发布内容供对话检索 |
| FR-12 反馈与审计 | 结果反馈、审计页 | Feedback & Audit | 反馈按钮在对话内，处理台独立 |

对话流只编排用户完成当前事项所需的“问、追问、检索、适用性、风险、办税、证据和草稿”。机构配置、批量知识治理、正式审核和审计不塞入聊天消息流，避免把工作台做成纯聊天壳。

---

## 5. 领域词汇与核心状态

### 5.1 必须区分的概念

| 概念 | 定义 |
|---|---|
| 系统使用者 | 机构成员，拥有账号和角色 |
| 被服务客户／事项主体 | 专业机构服务的企业或个体工商户，只以最小、虚构／脱敏画像存在 |
| 事项 Case | 一次可持续补充、分析、审核和归档的专业工作单元 |
| 会话 Conversation | 事项下的一段交互；一个事项可有多段会话 |
| 运行 Run | 针对一条问题执行一次路由、检索、规则和生成的可回放过程 |
| 政策文档 Document | 具有文号／发布机构／URL 的逻辑文件 |
| 文档版本 Document Version | 某次抓取并审核的内容快照 |
| 条款／片段 Chunk | 可引用和可检索的最小文本单元，必须属于特定文档版本 |
| FAQ | 经审核的标准问答知识资产；不是会话记忆，不是法源 |
| 机构经验 | 经审核且脱敏的案例摘要，只对本机构可见 |
| 知识快照 | 一组已发布文档、关系、FAQ、规则、办税事项版本的不可变清单 |

### 5.2 关键枚举

| 枚举 | 取值 |
|---|---|
| `source_level` | `A_LEGAL`、`B_INTERPRETATION`、`C_PROCEDURE`、`D_OFFICIAL_FAQ` |
| `policy_status` | `not_effective`、`effective`、`partially_effective`、`amended`、`repealed`、`expired`、`unknown` |
| `review_status` | `draft`、`pending_review`、`approved`、`published`、`rejected`、`retired` |
| `route_code` | `POLICY_LOOKUP`、`APPLICABILITY`、`MULTI_CONDITION_CONSULT`、`PROCEDURE`、`RISK_REVIEW`、`POLICY_TIMELINE`、`OUT_OF_SCOPE` |
| `applicability_result` | `preliminarily_applicable`、`not_applicable`、`need_more_information`、`conflict_manual_review` |
| `truth_value` | `true`、`false`、`unknown` |
| `risk_level` | `high`、`medium`、`low`、`info` |
| `review_decision` | `approve`、`conditional_approve`、`return`、`reject` |
| `run_status` | `queued`、`extracting_facts`、`waiting_for_facts`、`retrieving`、`evaluating_rules`、`generating`、`validating`、`pending_review`、`completed`、`failed`、`cancelled` |

---

## 6. MySQL 数据模型

### 6.1 公共字段约定

除纯关联表外，表默认包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `CHAR(36)` PK | UUIDv7 |
| `created_at`、`updated_at` | `DATETIME(3)` | UTC，数据库或仓储层统一写入 |
| `created_by`、`updated_by` | `CHAR(36)` NULL | 系统任务可为空 |
| `version_no` | `INT` | 需要乐观锁的聚合根使用，初始 1 |

所有 FK 列、状态列、`org_id`、`doc_no`、`region_code`、业务日期和创建时间都需按查询模式建索引。正式环境禁止依赖 ORM 自动建表，必须使用版本化 migration。

### 6.2 机构、身份与审计

#### `organizations`

| 字段 | 类型 | 约束／说明 |
|---|---|---|
| `id` | CHAR(36) | PK |
| `code` | VARCHAR(64) | 唯一机构代码，非工商统一信用代码 |
| `name` | VARCHAR(200) | 机构显示名 |
| `status` | VARCHAR(32) | active／suspended／closed |
| `settings_json` | JSON | TTL、默认地区、免责声明模板等低频配置 |
| `version_no` | INT | 乐观锁 |

索引：`UNIQUE(code)`、`INDEX(status)`。

#### `users`

| 字段 | 类型 | 约束／说明 |
|---|---|---|
| `id` | CHAR(36) | PK |
| `email` | VARCHAR(254) | 可空；非空时全局唯一 |
| `mobile_hash` | CHAR(64) | 可空，只存规范化手机号哈希用于查重 |
| `display_name` | VARCHAR(100) | 显示名 |
| `password_hash` | VARCHAR(255) | 强哈希；不得保存明文／可逆密文 |
| `status` | VARCHAR(32) | invited／active／locked／disabled |
| `last_login_at` | DATETIME(3) | 最近登录 |

索引：`UNIQUE(email)`、`INDEX(mobile_hash)`、`INDEX(status)`。

#### `organization_members`

| 字段 | 类型 | 约束／说明 |
|---|---|---|
| `org_id`、`user_id` | CHAR(36) | 联合唯一 |
| `role_code` | VARCHAR(32) | org_admin／consultant／reviewer／knowledge_admin／auditor |
| `status` | VARCHAR(32) | invited／active／disabled |
| `joined_at` | DATETIME(3) | 加入时间 |

索引：`UNIQUE(org_id,user_id)`、`INDEX(org_id,role_code,status)`。

#### `auth_sessions`

保存刷新会话而非访问令牌正文：`user_id`、`org_id`、`refresh_token_hash`、`device_label`、`expires_at`、`revoked_at`、`last_seen_at`。索引：`UNIQUE(refresh_token_hash)`、`INDEX(user_id,expires_at)`。

#### `audit_logs`

不可由普通用户修改或删除。字段：`org_id`、`actor_user_id`、`action_code`、`resource_type`、`resource_id`、`request_id`、`result`、`ip_hash`、`user_agent_hash`、`before_json`、`after_json`、`occurred_at`。对敏感文本只记录字段名、摘要和哈希，不复制完整问题。索引：`INDEX(org_id,occurred_at)`、`INDEX(resource_type,resource_id)`、`UNIQUE(request_id,id)`。

### 6.3 数据来源、文档与条款

#### `source_sites`

字段：`name`、`base_url`、`domain`、`source_level`、`authority_name`、`region_code`、`collection_method`（manual／whitelist_crawl／api／file_import）、`whitelist_rules_json`、`crawl_interval_minutes`、`status`、`last_checked_at`。`domain`＋`region_code` 唯一。

#### `ingestion_jobs`

字段：`source_site_id`、`job_type`、`trigger_type`、`source_url`、`input_object_key`、`dedupe_key`、`status`、`attempt_count`、`discovered_count`、`changed_count`、`error_code`、`error_detail_safe`、`started_at`、`finished_at`。`dedupe_key` 唯一，防止同一抓取重复执行。

#### `source_documents`

| 字段 | 类型 | 说明 |
|---|---|---|
| `canonical_key` | VARCHAR(255) | 规范文号＋发文机构；无文号时使用规范 URL 哈希，唯一 |
| `title` | VARCHAR(500) | 规范标题 |
| `doc_no` | VARCHAR(200) | 文号，可空 |
| `doc_type` | VARCHAR(64) | law／regulation／announcement／interpretation／guide／faq 等 |
| `source_level` | VARCHAR(32) | A—D |
| `issuing_authority` | VARCHAR(200) | 发文机构规范名 |
| `region_code` | VARCHAR(12) | 全国／省／市 |
| `publish_date` | DATE | 发布日期 |
| `effective_start`、`effective_end` | DATE | 可空；开区间由应用解释 |
| `policy_status` | VARCHAR(32) | 当前状态 |
| `canonical_url` | VARCHAR(1500) | 官方 URL |
| `current_version_id` | CHAR(36) | 当前已发布版本 |
| `review_status` | VARCHAR(32) | 文档逻辑对象状态 |

索引：`UNIQUE(canonical_key)`、`INDEX(doc_no)`、`INDEX(region_code,policy_status,effective_start,effective_end)`、`INDEX(source_level,doc_type)`。

#### `document_versions`

字段：`document_id`、`version_no`、`captured_at`、`source_url`、`raw_object_key`、`parsed_object_key`、`mime_type`、`http_etag`、`last_modified_header`、`content_hash_sha256`、`parser_version`、`parse_status`、`ocr_status`、`review_status`、`published_at`、`supersedes_version_id`。约束：`UNIQUE(document_id,version_no)`、`UNIQUE(document_id,content_hash_sha256)`。

#### `document_chunks`

| 字段 | 类型 | 说明 |
|---|---|---|
| `document_id`、`document_version_id` | CHAR(36) | 证据归属 |
| `source_chunk_id` | VARCHAR(100) | 稳定外部标识，如 `doc_uuid:v3:article_5:p2`，全局唯一 |
| `parent_chunk_id` | CHAR(36) | 章节／条款父块，可空 |
| `chunk_order` | INT | 文档顺序 |
| `chunk_type` | VARCHAR(32) | title／chapter／article／paragraph／table／attachment |
| `heading_path` | VARCHAR(1000) | 标题路径 |
| `clause_label` | VARCHAR(100) | 第几条／款／项，可空 |
| `content_text` | MEDIUMTEXT | 清洗后的可引用正文 |
| `content_hash_sha256` | CHAR(64) | 片段去重与更新判断 |
| `token_count` | INT | 指定 tokenizer 版本下的 token 数 |
| `char_start`、`char_end` | INT | 相对解析文本的定位 |
| `effective_start`、`effective_end` | DATE | 条款级日期覆盖，空则继承文档 |
| `region_code`、`policy_status`、`review_status` | VARCHAR | 检索硬过滤冗余字段 |
| `index_status` | VARCHAR(32) | pending／indexed／failed／removed |

索引：`UNIQUE(source_chunk_id)`、`INDEX(document_version_id,chunk_order)`、`INDEX(document_id,clause_label)`、`INDEX(review_status,policy_status,region_code)`。

#### `document_relations`

保存文档沿革台账：`from_document_id`、`relation_type`（cites／amends／replaces／repeals／partially_repeals）、`to_document_id`、`effective_date`、`source_chunk_id`、`extracted_by`、`extraction_confidence DECIMAL(5,4)`、`review_status`、`publish_batch_id`。约束：同一版本、主客体、关系、来源片段联合唯一。

### 6.4 受控知识、条件与图关系台账

#### `controlled_terms`

保存税种、主体形态、增值税身份、资格、行业、经营行为、义务等受控词：`term_type`、`code`、`canonical_name`、`aliases_json`、`parent_term_id`、`region_code`、`status`。约束：`UNIQUE(term_type,code)`。

#### `knowledge_objects`

字段：`object_type`（tax_benefit／tax_obligation／business_action／procedure_ref 等）、`code`、`canonical_name`、`region_code`、`current_version_id`、`status`。它不用于替代文档和条款，只承载需要跨文档合并的业务对象。

#### `knowledge_object_versions`

字段：`knowledge_object_id`、`version_no`、`effective_start`、`effective_end`、`attributes_json`、`review_status`、`supersedes_version_id`、`published_at`。约束：`UNIQUE(knowledge_object_id,version_no)`。已发布属性变化产生新版本，避免知识快照引用到可变对象。

#### `knowledge_relations`

字段：`subject_type`、`subject_id`、`predicate`、`object_type`、`object_id`、`qualifiers_json`、`source_document_id`、`source_chunk_id`、`effective_start`、`effective_end`、`extraction_method`、`extraction_confidence`、`review_status`、`publish_batch_id`。所有正式关系必须有 `source_chunk_id`；人工建立的分类关系如无单条法源，也必须引用治理说明文档。索引：`INDEX(subject_type,subject_id,predicate)`、`INDEX(object_type,object_id,predicate)`、`INDEX(review_status,publish_batch_id)`。

#### `condition_sets`

用于优惠、规则、义务的可审核条件组：`owner_type`、`owner_id`、`version_no`、`condition_kind`（applicability／exclusion／trigger）、`expression_json`、`human_readable_text`、`source_chunk_id`、`review_status`。`expression_json` 使用第 12.7 节的规则 DSL；不得只保存一段无法执行的自然语言。

### 6.5 FAQ 与机构经验

#### `faqs`

| 字段 | 类型 | 说明 |
|---|---|---|
| `org_id` | CHAR(36) NULL | NULL 为官方／全局 FAQ；非空为机构 FAQ |
| `faq_type` | VARCHAR(32) | official／institutional |
| `faq_code` | VARCHAR(64) | 机构范围内稳定编码 |
| `current_version_id` | CHAR(36) | 当前已发布／可编辑版本指针 |
| `status` | VARCHAR(32) | active／retired |
| `availability_status` | VARCHAR(32) | available／impact_review_required／suspended |
| `source_document_id` | CHAR(36) NULL | 官方 FAQ 来源文档 |

索引：`UNIQUE(org_id,faq_code)`；MySQL 对 NULL 的唯一语义需用生成列或应用约束保证全局 FAQ code 唯一，另建 `INDEX(org_id,status,availability_status)`。

#### `faq_versions`

一条记录代表不可变 FAQ 内容版本：`faq_id`、`version_no`、`standard_question`、`standard_answer`、`scope_json`、`region_code`、`effective_start`、`effective_end`、`policy_status`（由证据状态计算）、`review_status`、`evidence_version_hash`、`supersedes_version_id`、`published_at`。约束：`UNIQUE(faq_id,version_no)`；索引：`INDEX(review_status,region_code,policy_status,effective_start,effective_end)`。发布后正文和范围不得原地更新。

#### `faq_variants`

字段：`faq_version_id`、`variant_text`、`variant_text_hash`、`variant_source`（official／editor／approved_case／llm_suggested）、`language`、`review_status`、`index_status`。LLM 只能产生 `llm_suggested` 草稿，审核后才可发布。约束：`UNIQUE(faq_version_id,variant_text_hash)`。

#### `faq_evidence_links`

字段：`faq_version_id`、`document_id`、`document_version_id`、`chunk_id`、`evidence_role`（primary／supporting／procedure）、`claim_scope`、`review_status`。正式 FAQ 版本至少一条 primary 证据；D 级官方热点问答不能单独支撑重大适用性结论。

#### `approved_case_memories`

机构内长期经验：`org_id`、`source_case_id`、`title`、`anonymized_summary`、`fact_pattern_json`、`approved_answer`、`region_code`、`business_date_from/to`、`review_status`、`approved_by`、`approved_at`、`index_status`。只有审核人明确执行“沉淀为机构经验”且通过脱敏检查后创建；不可自动由会话生成。

### 6.6 办税事项

#### `tax_procedures`

字段：`procedure_code`、`name`、`tax_type_code`、`region_code`、`channel_type`、`current_version_id`、`review_status`。约束：`UNIQUE(procedure_code,region_code)`。

#### `tax_procedure_versions`

字段：`procedure_id`、`version_no`、`conditions_text`、`deadline_text`、`channel_text`、`common_errors_json`、`effective_start/end`、`review_status`、`published_at`。约束：`UNIQUE(procedure_id,version_no)`。

#### `procedure_steps`

字段：`procedure_version_id`、`step_no`、`title`、`instruction_text`、`channel_ref`、`source_chunk_id`。约束：`UNIQUE(procedure_version_id,step_no)`。

#### `procedure_materials`

字段：`procedure_version_id`、`material_code`、`material_name`、`required_flag`、`condition_expression_json`、`copies_text`、`format_text`、`source_chunk_id`。条件材料必须可说明“何时需要”。

#### `procedure_evidence_links`

字段：`procedure_version_id`、`chunk_id`、`evidence_role`、`review_status`。

### 6.7 风险规则

#### `risk_rules`

字段：`rule_code`、`name`、`category`（tax_obligation／invoice／filing／benefit／validity／retention／conflict）、`tax_type_code`、`region_code`、`current_version_id`、`status`。`rule_code` 全局唯一且发布后不可复用。

#### `risk_rule_versions`

| 字段 | 类型 | 说明 |
|---|---|---|
| `risk_rule_id`、`version_no` | — | 联合唯一 |
| `severity` | VARCHAR(16) | high／medium／low／info |
| `scope_expression_json` | JSON | 规则适用范围 |
| `trigger_expression_json` | JSON | 三值逻辑触发式 |
| `missing_fact_policy` | VARCHAR(32) | need_info／not_hit／manual_review |
| `explanation_template` | TEXT | 规则命中说明模板 |
| `recommendation_template` | TEXT | 处理建议模板 |
| `effective_start/end` | DATE | 规则有效期 |
| `review_status` | VARCHAR(32) | 生命周期 |
| `checksum` | CHAR(64) | 规则版本不可变校验 |

#### `risk_rule_evidences`

字段：`rule_version_id`、`chunk_id`、`evidence_role`（basis／exception／procedure）、`claim_scope`。每个发布版本至少一条 basis。

#### `risk_rule_test_cases`

字段：`rule_version_id`、`case_name`、`facts_json`、`expected_truth_value`、`expected_severity`、`expected_missing_facts_json`、`test_type`（positive／negative／boundary／missing）、`last_run_result`、`last_run_at`。发布门禁要求该版本全部测试通过。

### 6.8 事项、会话与记忆

#### `consultation_cases`

字段：`org_id`、`case_no`、`title`、`status`、`owner_user_id`、`reviewer_user_id`、`default_region_code`、`current_profile_version`、`current_draft_id`、`opened_at`、`closed_at`、`version_no`。约束：`UNIQUE(org_id,case_no)`；索引：`INDEX(org_id,status,owner_user_id,updated_at)`。

#### `case_subject_profiles`

一条记录代表不可变画像版本。字段：`org_id`、`case_id`、`profile_version`、`legal_form_code`、`vat_taxpayer_type`、`small_low_profit_status`（yes／no／unknown）、`industry_code`、`region_code`、`business_date`、`business_action_codes_json`、`extra_attributes_json`、`confirmation_status`、`confirmed_by`、`confirmed_at`、`supersedes_profile_id`。约束：`UNIQUE(case_id,profile_version)`。

#### `case_facts`

字段：`org_id`、`case_id`、`profile_version`、`fact_key`、`value_type`、`value_json`、`unit`、`source_type`（user_input／extracted／reviewer）、`source_message_id`、`confirmation_status`（proposed／confirmed／rejected／superseded）、`confidence`、`effective_date`、`confirmed_by/at`。同一 profile_version＋fact_key 可以保存候选历史，但仅一个 confirmed。

#### `conversations`

字段：`org_id`、`case_id`、`title`、`status`、`started_by`、`last_message_at`、`summary_version`。索引：`INDEX(org_id,case_id,last_message_at)`。

#### `messages`

字段：`org_id`、`conversation_id`、`case_id`、`sequence_no BIGINT`、`role`（user／assistant／system_visible）、`content_text MEDIUMTEXT`、`content_json`、`run_id`、`parent_message_id`、`visibility`、`content_hash`、`redaction_status`、`created_at`。约束：`UNIQUE(conversation_id,sequence_no)`。不得保存隐藏思维链；系统可见消息只记录阶段和可解释原因。

#### `conversation_summaries`

字段：`org_id`、`conversation_id`、`summary_version`、`covered_from_sequence`、`covered_to_sequence`、`summary_text`、`confirmed_facts_json`、`open_questions_json`、`generated_by_model_version`、`review_status`。摘要是压缩上下文，不替代 `case_facts`。

### 6.9 查询运行、证据、答案与审核

#### `analysis_runs`

| 字段 | 类型 | 说明 |
|---|---|---|
| `org_id`、`case_id`、`conversation_id`、`request_message_id` | CHAR(36) | 运行上下文 |
| `status` | VARCHAR(32) | 运行状态 |
| `public_knowledge_snapshot_id` | CHAR(36) | 固定公共政策／规则／办税知识版本 |
| `org_knowledge_snapshot_id` | CHAR(36) NULL | 固定本机构 FAQ／经验版本；机构尚无快照时为空 |
| `profile_version` | INT | 固定事项事实版本 |
| `model_profile_id`、`prompt_bundle_version` | CHAR／VARCHAR | 复现生成 |
| `router_version`、`retrieval_config_version` | VARCHAR(64) | 复现路由与召回 |
| `request_id`、`idempotency_key` | VARCHAR | 幂等与追踪 |
| `started_at`、`completed_at` | DATETIME(3) | 耗时 |
| `error_code`、`error_detail_safe` | VARCHAR／TEXT | 安全错误信息 |

约束：`UNIQUE(org_id,idempotency_key)`（非空）；索引：`INDEX(org_id,case_id,created_at)`、`INDEX(status,created_at)`。

#### `run_routes`

字段：`run_id`、`route_code`、`subquery_no`、`subquery_text`、`required_facts_json`、`missing_facts_json`、`route_confidence`、`route_reason_codes_json`、`status`。复杂咨询允许多个 route 记录。

#### `retrieval_results`

字段：`run_id`、`route_id`、`retriever_type`（exact／dense／bm25／faq／graph／rule）、`candidate_type`、`candidate_id`、`document_version_id`、`chunk_id`、`rank_no`、`raw_score`、`rrf_score`、`rerank_score`、`filter_snapshot_json`、`selected_flag`、`rejection_reason`。它是运行回放的核心，不只保存最终 8 条。

#### `risk_findings`

字段：`org_id`、`run_id`、`rule_version_id`、`truth_value`、`risk_level`、`triggered_facts_json`、`missing_facts_json`、`evidence_ids_json`、`explanation_text`、`manual_review_required`。规则结果为事实，LLM 只可生成 `explanation_text`，不得改前述字段。

#### `answer_drafts`

字段：`org_id`、`case_id`、`run_id`、`draft_version`、`draft_type`（analysis／client_reply／procedure_guide）、`content_markdown MEDIUMTEXT`、`structured_output_json`、`confidence_dimensions_json`、`disclaimer_version`、`status`、`parent_draft_id`、`generated_at`、`edited_by`、`version_no`。

#### `answer_claims`

将草稿拆为可审核主张：`draft_id`、`claim_no`、`claim_type`（policy／applicability／risk／procedure／recommendation）、`claim_text`、`importance`（key／supporting）、`validation_status`、`validation_reasons_json`、`manual_review_required`。约束：`UNIQUE(draft_id,claim_no)`。

#### `claim_evidences`

字段：`claim_id`、`evidence_type`（chunk／faq／rule／graph_path）、`evidence_id`、`document_version_id`、`chunk_id`、`entailment_status`、`citation_label`、`quoted_span_start/end`、`source_url_snapshot`。关键 policy 主张至少一条通过验证的条款证据。

#### `review_tasks`

字段：`org_id`、`resource_type`（case_draft／faq／risk_rule／knowledge_batch／procedure）、`resource_id`、`assigned_to`、`status`（pending／in_review／completed／cancelled）、`priority`、`due_at`、`submitted_by/at`、`completed_at`。索引：`INDEX(org_id,assigned_to,status,priority)`。

#### `review_actions`

追加式记录：`org_id`、`review_task_id`、`reviewer_user_id`、`decision`、`target_type`（whole／claim／evidence／field）、`target_id`、`comment_text`、`before_version`、`after_version`、`created_at`。审核历史不可覆盖。

#### `feedback_tickets`

字段：`org_id`、`reporter_user_id`、`source_type`、`source_id`、`category`（wrong_policy／outdated／wrong_region／unsupported_claim／bad_route／missing_knowledge／other）、`description`、`severity`、`status`、`assigned_to`、`resolution_type`、`linked_knowledge_object_id`、`created_at`、`resolved_at`。

### 6.10 发布、复现与跨存储同步

#### `knowledge_snapshots`

字段：`org_id`（NULL 表示公共知识，非空表示机构知识）、`snapshot_code`、`snapshot_type`（public／organization）、`status`（building／validating／active／failed／retired）、`base_snapshot_id`、`description`、`manifest_hash`、`activated_at`、`activated_by`。任一时刻只有一个公共 active 快照；每个机构至多一个机构 active 快照。机构快照只列 FAQ／经验等私有资产，不复制公共政策内容。

#### `knowledge_snapshot_items`

字段：`snapshot_id`、`item_type`（document_version／relation_batch／faq_version／approved_case_memory／rule_version／procedure_version／prompt_bundle）、`item_id`、`item_version`、`checksum`。约束：`UNIQUE(snapshot_id,item_type,item_id)`。

#### `knowledge_publish_batches`

字段：`batch_type`、`scope`、`org_id`、`status`、`candidate_count`、`approved_count`、`rejected_count`、`validation_report_json`、`submitted_by`、`approved_by`、`published_at`。

#### `outbox_events`

字段：`aggregate_type`、`aggregate_id`、`event_type`、`payload_json`、`dedupe_key`、`status`（pending／processing／done／dead）、`attempt_count`、`next_attempt_at`、`locked_by`、`locked_at`、`last_error_safe`、`created_at`。约束：`UNIQUE(dedupe_key)`；索引：`INDEX(status,next_attempt_at)`。

#### `projection_sync_states`

字段：`projection_type`（milvus_policy／milvus_faq／milvus_case／neo4j_graph）、`aggregate_type`、`aggregate_id`、`source_version`、`target_version`、`status`、`last_event_id`、`synced_at`、`error_safe`。用于一致性巡检和重建。

#### `model_profiles` 与 `prompt_versions`

- `model_profiles`：`provider`、`model_name`、`purpose`、`parameters_json`、`status`、`config_version`，密钥只存密钥引用，不能进表。
- `prompt_versions`：`prompt_code`、`version_no`、`template_text`、`input_schema_json`、`output_schema_json`、`checksum`、`review_status`、`published_at`。提示词修改必须版本化并跑金标准；不得把税务规则藏在提示词中。

---

## 7. Milvus 集合设计

Milvus 中每条记录都来自已发布 MySQL 资产；删除采用“先在 MySQL 停用、再删除／标记索引”，线上查询仍以 MySQL 状态复核。集合名带模型／schema 版本，并通过 alias 切换稳定版本。

### 7.1 `policy_chunks_v1`

| 字段 | Milvus 类型 | 用途 |
|---|---|---|
| `chunk_id` | VARCHAR PK | 对应 MySQL `document_chunks.id` |
| `source_chunk_id` | VARCHAR | 对外稳定证据 ID |
| `document_id`、`document_version_id` | VARCHAR | 追溯与版本过滤 |
| `parent_chunk_id` | VARCHAR | 父块回填 |
| `doc_no`、`title`、`clause_label`、`heading_path` | VARCHAR | 展示与精确辅助 |
| `content` | VARCHAR（足够长度） | BM25 分词文本和候选返回 |
| `dense_vector` | FLOAT_VECTOR(1024) | BGE-M3 稠密向量 |
| `sparse_vector` | SPARSE_FLOAT_VECTOR | 由 Milvus BM25 function 生成 |
| `source_level`、`doc_type` | VARCHAR | 权威性过滤／加权 |
| `region_code`、`policy_status`、`review_status` | VARCHAR | 硬过滤 |
| `effective_start_int`、`effective_end_int` | INT64 | `YYYYMMDD`；空值用约定边界表示 |
| `tax_type_codes`、`subject_codes`、`action_codes` | ARRAY<VARCHAR> | 受控标签过滤 |
| `content_hash`、`embedding_version`、`snapshot_code` | VARCHAR | 一致性与复现 |

索引建议：稠密向量 MVP 用 HNSW 或 AUTOINDEX；稀疏向量使用 Milvus 支持的 sparse inverted index；标量字段建立适用索引。具体 `M/efConstruction/ef` 不在未测数据量前硬编码，通过 200—300 道金标准做召回／延迟调优。

### 7.2 `faq_questions_v1`

| 字段 | 类型 | 用途 |
|---|---|---|
| `faq_variant_id` | VARCHAR PK | 一条问题变体一个向量 |
| `faq_id` | VARCHAR | 回查 FAQ 正文 |
| `org_id` | VARCHAR | `GLOBAL` 或机构 UUID，强制过滤 |
| `question_text` | VARCHAR | BM25 与展示 |
| `dense_vector`、`sparse_vector` | 1024 维／稀疏 | 混合 FAQ 召回 |
| `faq_type`、`region_code`、`policy_status`、`review_status` | VARCHAR | 硬过滤 |
| `effective_start_int`、`effective_end_int` | INT64 | 业务日期过滤 |
| `subject_codes`、`tax_type_codes` | ARRAY<VARCHAR> | 适用范围 |
| `evidence_version_hash`、`embedding_version` | VARCHAR | 证据变化时强制重建 |

查询必须使用 `(org_id == GLOBAL OR org_id == current_org)`，并在 API 仓储层构造，不接受客户端传入原始 filter 表达式。

### 7.3 `approved_case_memories_v1`

字段：`memory_id` PK、`org_id`、`title`、`anonymized_summary`、`dense_vector`、可选 `sparse_vector`、`region_code`、`business_date_from_int/to_int`、`fact_pattern_codes`、`review_status`、`evidence_hash`、`embedding_version`。只检索本机构 `published` 且通过脱敏检查的经验；MVP 不跨机构共享。

### 7.4 检索参数基线

- 条款稠密 Top 30、BM25 Top 30；FAQ Top 10；机构经验 Top 5。
- 合并后去重并保留 30—40 条给 reranker；最终进入证据包 8—12 条。
- `dense_vector` 必须归一化策略一致；模型或 tokenizer 改变即提升 `embedding_version`。
- 任何业务日期／地域／审核／政策状态过滤都在 ANN 搜索表达式中先执行，不能只在生成后过滤。

---

## 8. Neo4j 图模型

### 8.1 MVP 节点

| Label | 主键／重要属性 | 说明 |
|---|---|---|
| `PolicyDocument` | `id`、`doc_no`、`title`、`policy_status`、`region_code` | 已发布政策逻辑文件 |
| `Clause` | `id`、`source_chunk_id`、`document_version_id`、`clause_label` | 可追溯条款 |
| `TaxType` | `code`、`name` | 受控税种 |
| `TaxBenefit` | `id`、`name`、`valid_from/to` | 优惠对象 |
| `TaxObligation` | `id`、`name` | 涉税义务 |
| `BusinessAction` | `code`、`name` | 受控经营行为 |
| `Procedure` | `id`、`name`、`region_code` | 办税事项 |
| `Material` | `id`、`name` | 办理材料，仅首批事项 |
| `RiskRule` | `id`、`rule_code`、`version_no` | 规则版本引用节点 |
| `FAQ` | `id`、`faq_type`、`org_scope` | MVP 建议仅投影官方 FAQ；机构 FAQ 关系先由 MySQL 查询，避免图租户泄露 |
| `Region`、`SubjectTerm` | `code`、`name` | 受控维度，不建设庞大本体 |

不把客户、会话、咨询事项、未审核抽取结果写入公共政策图。

### 8.2 MVP 关系

| 关系 | 方向 | 用途 |
|---|---|---|
| `HAS_CLAUSE` | Document→Clause | 文件条款定位 |
| `CITES`、`AMENDS`、`REPLACES`、`REPEALS`、`PARTIALLY_REPEALS` | Document→Document | 沿革和版本时间线 |
| `INVOLVES_TAX` | Clause／Benefit／Obligation→TaxType | 跨税种展开 |
| `SUPPORTED_BY` | Benefit／Obligation／RiskRule／Procedure／FAQ→Clause | 证据追溯 |
| `APPLIES_TO` | Benefit／Clause→SubjectTerm／Region | 受控适用范围；复杂条件仍在 `condition_sets` |
| `TRIGGERS` | BusinessAction→TaxObligation | 从事实到义务 |
| `CORRESPONDS_TO` | TaxObligation→Procedure | 从义务到办理 |
| `REQUIRES_MATERIAL` | Procedure→Material | 办理材料 |

所有关系属性包含：`relation_id`（对应 MySQL 台账 ID）、`source_document_id`、`source_chunk_id`、`valid_from`、`valid_to`、`review_status`、`confidence`、`publish_batch_id`。没有来源的抽取候选不得投影。

### 8.3 约束与查询安全

- 每类节点的 `id`／`code` 建唯一约束；`doc_no`、`source_chunk_id`、`policy_status`、`region_code` 建范围或文本查询所需索引。
- Neo4j 支持属性唯一性／存在性约束和搜索性能索引，实现时按官方 [约束](https://neo4j.com/docs/cypher-manual/current/schema/constraints/) 与 [索引](https://neo4j.com/docs/cypher-manual/current/indexes/search-performance-indexes/) 文档建迁移脚本。
- 在线图检索只允许预定义 Cypher 模板和白名单关系；禁止将用户文本拼接为 Cypher。
- 默认最大路径深度 2，沿革链可到 4；必须设置节点上限、超时和环检测。
- 图返回的每条路径必须转换为包含 `source_chunk_id` 的 EvidencePath；无证据边在生成前丢弃。
- MVP 官方公共图不承载机构私有关系。若后续将机构知识写图，必须采用独立数据库或强制 `org_id` 图投影与自动租户测试。

---

## 9. Redis 与会话长短期记忆

### 9.1 Key 设计

| Key 模式 | 内容 | TTL |
|---|---|---|
| `tm:session:{org_id}:{conversation_id}` | 最近 10—20 条消息摘要、当前事项版本、当前路由、待追问事实 | 72 小时，可配置 |
| `tm:run:{run_id}:state` | LangGraph 当前状态、节点、重试次数、临时证据 ID | 完成后 24 小时；运行中续期 |
| `tm:run:{run_id}:events` | SSE 最近事件游标／短期重放 | 24 小时 |
| `tm:checkpoint:{thread_id}:*` | LangGraph checkpointer 命名空间 | 会话结束后 72 小时 |
| `tm:cache:policy:{hash}` | 政策详情／时间线热点缓存 | 5—30 分钟 |
| `tm:cache:retrieval:{snapshot}:{hash}` | 无私有事实的公共检索结果 | 5—15 分钟 |
| `tm:lock:{resource_type}:{id}` | 发布、索引、审核锁 | 30—300 秒，带 owner token |
| `tm:rate:{org_id}:{user_id}:{window}` | 限流计数 | 对应窗口＋缓冲 |
| `tm:celery:*` | 队列 broker／结果后端 | 按 Celery 策略；与业务 key 前缀隔离 |

### 9.2 记忆管理规则

1. 用户消息先写 MySQL，提交成功后再更新 Redis；不能只写缓存。
2. LLM 抽取到的事实先作为 `proposed`，展示给用户确认；确认后写 `case_facts` 新版本。
3. 短期上下文由“最近消息＋最新摘要＋已确认事实＋当前运行状态”构成，不把整个历史无限塞给模型。
4. 当消息超过 20 条或估算上下文超过阈值时生成新摘要；摘要覆盖范围不可重叠冲突，旧摘要保留供回放。
5. Redis 丢失时，从 MySQL 最近消息、摘要、事项画像和未完成运行重建；流式增量可能无法恢复，但已保存阶段结果不丢失。
6. 跨会话召回只检索审核 FAQ 和 `approved_case_memories`；普通聊天、未审核草稿和被退回答案不得建立长期向量索引。
7. 政策更新不会静默改写历史事项。新运行使用新快照；历史运行仍引用旧 `public_knowledge_snapshot_id` 与 `org_knowledge_snapshot_id`，界面额外提示“存在较新政策／机构知识”。

LangGraph 的 thread-scoped checkpointer 与 cross-thread store 的职责需区分。TaxMind Pro 中 Redis checkpointer 只用于工作流恢复，真正的长期事项记忆仍由 MySQL 持久化；相关机制参考 [LangGraph Memory](https://docs.langchain.com/oss/python/langgraph/add-memory)。

---

## 10. MinIO 对象设计

| Bucket | 对象 | 路径建议 | 生命周期 |
|---|---|---|---|
| `taxmind-raw` | 原始 HTML、PDF、附件、图片 | `{source_site_id}/{document_id}/{version_id}/raw/{sha256}.{ext}` | 长期保留；开启版本化 |
| `taxmind-parsed` | 解析文本、版面 JSON、OCR、表格结构 | `{document_id}/{version_id}/{parser_version}/...` | 随文档版本长期保留 |
| `taxmind-exports` | 经授权导出的内部草稿／审核包 | `{org_id}/{case_id}/{draft_id}/...` | 默认 30—90 天后删除，可配置 |
| `taxmind-temp` | 上传中间件、OCR 临时页 | `{job_id}/...` | 24—72 小时自动清理 |

规则：

- Bucket 默认私有；前端通过短时签名 URL 访问，签名 URL 不写审计正文。
- MySQL 保存 `object_key`、`sha256`、`mime_type`、大小和上传者；不保存永久公网 URL。
- 上传前校验 MIME、扩展名、大小和恶意文件；PDF／图片只进入离线解析队列。
- 原件不得被后续清洗结果覆盖；任何重解析产生新 `parser_version` 路径。
- 对外不提供官方资料整库下载。

---

## 11. 跨存储一致性与发布流程

### 11.1 Outbox 事件

| 事件 | 目标投影 | 消费动作 |
|---|---|---|
| `DOCUMENT_VERSION_PUBLISHED` | Milvus、Neo4j | 建条款向量；投影文件／条款节点和沿革边 |
| `DOCUMENT_VERSION_RETIRED` | Milvus、Neo4j | 停用／删除对应版本并更新状态 |
| `FAQ_PUBLISHED` | Milvus；官方 FAQ 可进 Neo4j | 建问题变体索引并绑定证据 |
| `FAQ_RETIRED` | Milvus、Neo4j | 删除或停用索引与关系 |
| `RULE_VERSION_PUBLISHED` | Neo4j（引用关系） | 更新 RiskRule→Clause 投影 |
| `PROCEDURE_VERSION_PUBLISHED` | Neo4j | 更新事项、材料、依据投影 |
| `CASE_MEMORY_PUBLISHED` | Milvus | 仅写本机构经验索引 |
| `SNAPSHOT_ACTIVATED` | API／缓存 | 原子切换 alias／snapshot，清除相关缓存 |

### 11.2 发布原子性

1. 对候选资产完成 schema 校验、来源校验、规则测试、引用可达性和租户检查。
2. 创建 `knowledge_snapshot(status=building)` 与不可变 manifest。
3. Worker 在版本化 Milvus collection／Neo4j batch 中构建投影，记录 `projection_sync_states`。
4. 运行抽样与金标准 smoke test。
5. 全部通过后，事务内将 snapshot 置 active、旧快照置 retired，并发出 `SNAPSHOT_ACTIVATED`。
6. 失败时保持上一 active 快照不变；清理未完成投影或保留供诊断。

MVP 可先在同一 Milvus collection 以 `snapshot_code` 过滤，但上线前必须证明切换期间不会混用新旧版本。更稳妥的实现是 versioned collection＋alias。

---

## 12. 关键算法方案

### 12.1 采集去重与版本发现

**文档身份：**

1. 有文号：`normalized(doc_no) + issuing_authority` 作为主要身份；标题和日期用于冲突检查。
2. 无文号：官方规范 URL 去除追踪参数后取哈希；URL 变化时用标题、机构、发布日期和正文指纹找候选合并。
3. 同一逻辑文件内容哈希未变，只更新 `last_checked_at`；哈希改变则创建 `document_version`，不覆盖旧版。
4. 新版解析后比较条款级哈希，生成 added／modified／removed 差异和影响对象清单。

**状态影响：**若发现修改、替代、废止或有效期变化，建立候选沿革关系；在人工审核前旧正式状态不自动改写，但系统对受影响内容显示“更新待核实”。审核发布后触发 FAQ、规则、办税事项和历史答案的影响扫描。

### 12.2 清洗与父子分块

1. 优先按 HTML heading、条／款／项、PDF 书签、版面坐标重建结构，禁止只按固定字符长度切块。
2. 父块为文件／章节／完整条款，子块为可独立引用的款／项／段；不得切断文号、条件列表、例外和表格行列关系。
3. 子块目标 300—600 tokens；完整短条款保持整体；超过 900 tokens 才按款项细分。
4. 相邻重叠 50—100 tokens 仅用于普通解释性段落；法律条款采用父子关系回填，避免重叠制造重复证据。
5. 表格单独存 `chunk_type=table`，同时保留表头和行上下文；附件与正文通过 heading path 关联。
6. 每块保留 `document_version_id`、`source_chunk_id`、标题路径、条号、字符位置和哈希。

### 12.3 实体与关系抽取

采用“确定性规则优先＋LLM 候选＋标准化＋人工审核”：

1. 规则抽取文号、机构、日期、条号、显式引用词（根据／自／废止／修改等）和行政区划。
2. LLM 只输出符合 JSON Schema 的候选：对象类型、规范名候选、关系、限定条件、原文 span、置信度。
3. 通过受控词表做别名归一；无法唯一消歧的候选标记 `ambiguous`，不能发布。
4. 关系必须绑定 `source_chunk_id` 和原文 span；低于阈值或涉及沿革／排除条件的候选强制人工审核。
5. 发布前验证两端对象存在、日期区间合法、沿革无矛盾环、关系谓词在白名单。
6. Neo4j 只接收 `published` 关系。

### 12.4 FAQ 构建与使用

**来源：**官方热点问答可由文档处理链产生候选；机构 FAQ 只能由知识管理员创建，或从已审核事项显式“沉淀”。

**发布条件：**标准问题、标准答案、适用地区、业务日期、主体范围、至少一条正式证据、审核人和版本齐全；政策证据发生变化后 FAQ 自动转 `impact_review_required`，在复核前只作为低优先候选或停止命中。

**命中算法：**

1. 用当前机构＋GLOBAL、地区、日期、主体、`published` 做硬过滤。
2. 对标准问题和变体执行稠密＋BM25 召回，取 Top 10。
3. reranker 比较用户问题与 FAQ 标准问题／适用范围；高相似只代表“候选”，不直接返回答案。
4. 回查 MySQL 正文和 `faq_evidence_links`，再次核验政策状态、地区、主体和日期。
5. 若 FAQ 与当前事实完全匹配，可作为答案骨架；若部分匹配，只用于召回扩展和追问，不复制确定结论。

### 12.5 七类业务路由

路由不是由问题长短决定，而由任务目标和必需事实决定。

| 路由 | 优先识别 | 主要检索计划 |
|---|---|---|
| 明确政策查询 | 文号、标题、条款、关键词 | MySQL 精确元数据→Milvus BM25／dense→文档详情 |
| 政策适用性 | 主体、税务身份、地区、业务日期、行为、数值条件 | 条款混合检索＋优惠／条件图＋条件引擎 |
| 多条件咨询 | 多个动作或多个问句、多个税种目标 | 拆子问题；每个子问题独立路由，再合并 |
| 办税流程 | 事项名、地区、办理时间、主体 | MySQL procedure 精确＋Milvus 条款＋Neo4j 事项证据 |
| 事项风险审查 | 经营行为、已确认事实、审查意图 | 规则 scope 过滤→规则执行→证据检索／图解释 |
| 版本与有效期 | “当时／现行／废止／替代”、文号、业务日期 | MySQL 版本＋Neo4j 沿革模板＋原文条款 |
| 超范围／证据不足 | 排除行业、跨境复杂事项、请求自动申报、关键法源缺失 | 拒答／转人工，不进入一般生成 |

**分类流程：**先用文号正则、显式意图词、范围清单和已确认事实做确定性分类；再由 LLM 输出多标签路由 JSON 和理由代码。两者冲突时优先安全路由：适用性／风险／版本类不得降级为普通 FAQ。路由置信度低或缺 P0 事实时暂停追问。

### 12.6 事实闸门与问题拆解

事实优先级：业务日期＞地区＞主体形态／税务身份＞经营行为＞数值条件＞行业特殊性。一个运行最多连续追问 3 轮；仍不完整时输出“已知、未知、不能判断、建议人工核实”。

多条件咨询拆解规则：

- 每个子问题只对应一个主要目标（适用性、发票、申报、流程、风险、版本）。
- 子问题继承已确认公共事实，但可以声明额外必需事实。
- 各子问题分别形成证据包和结论，合并阶段只能做去重与表述协调，不能让一个子问题的证据替另一个子问题背书。

### 12.7 条件与风险规则 DSL

规则 JSON 只允许白名单操作符：

- 组合：`all`、`any`、`not`；
- 比较：`eq`、`ne`、`in`、`not_in`、`gt`、`gte`、`lt`、`lte`、`between`、`exists`；
- 时间：`date_between`、`before`、`after`；
- 集合：`contains_any`、`contains_all`。

叶子条件引用受控 `fact_key`，禁止执行任意表达式、脚本或 SQL。计算采用三值逻辑：

| 运算 | 规则 |
|---|---|
| `all` | 任一 false→false；无 false 且有 unknown→unknown；全 true→true |
| `any` | 任一 true→true；无 true 且有 unknown→unknown；全 false→false |
| `not` | true／false 取反，unknown 仍 unknown |

适用性四态映射：

- 必要条件全 true 且排除条件全 false：`preliminarily_applicable`；
- 任一必要条件 false，或任一排除条件 true：`not_applicable`；
- 无决定性 false／排除 true，但存在 unknown：`need_more_information`；
- 法源、版本或条件表达存在实质冲突：`conflict_manual_review`。

风险规则执行顺序：scope→trigger→missing fact policy→证据绑定→等级模板。LLM 只能把 `triggered_facts`、规则模板和条款证据改写成易读说明，不能改 `truth_value`、`risk_level` 或 `rule_version_id`。

### 12.8 GraphRAG 检索与证据融合

**阶段 A：硬过滤。** 从事项画像得到 `business_date`、`region_code`、主体、税务身份和当前知识快照；排除未发布、日期不覆盖、地区不兼容、明确主体不符的候选。

**阶段 B：并行召回。** 默认 dense Top 30、BM25 Top 30、FAQ Top 10；精确文号和结构化办税事项从 MySQL 召回；图谱仅按路由执行白名单模板。

**阶段 C：秩融合。** 对各检索器结果使用加权 RRF：

`RRF(d) = Σ_i w_i / (k + rank_i(d))`，基线 `k=60`。明确文号查询提高 exact／BM25 权重；模糊行为提高 dense／graph 权重；FAQ 不能盖过不匹配的正式条款。

**阶段 D：重排与规则加权。** 对合并后的前 30—40 条运行 reranker，再组合权威性、时效、地域和审核状态：相关性仍是主因，A 级法源和完全匹配范围用于稳定排序，而不是救回语义无关结果。

**阶段 E：父块和图证据展开。** 子块命中后回填完整条款／章节；沿革、优惠条件、义务和办税关系最多展开 2 跳，去环并限制节点数。

**阶段 F：证据包。** 以 `chunk_id` 去重，保留命中原因、检索器、分数、法源级别、日期、地区、父块、图路径和冲突标记。最终选 8—12 条；每条必须可打开原文定位。

GraphRAG 不是“Neo4j 查一次＋向量查一次＋拼接”。图查询由向量候选中的实体／文件锚点触发，图路径反向扩展新的条款证据，再与原召回统一重排和冲突校验；最终生成只消费标准 EvidenceBundle。

### 12.9 冲突检测

以下任一情况建立 `evidence_conflict`：

- 同一业务日期同一事项出现 `effective` 与 `repealed/expired` 的状态冲突；
- 全国规则与地方操作口径结论不一致，且地方资料不能解释为办理差异；
- 新旧文沿革关系未审核或形成循环；
- FAQ 答案与其绑定条款条件不一致；
- 两条 A 级证据对关键条件给出不兼容表达。

冲突不由 LLM 自主裁决。可确定优先级的仅按明确法律层级／生效关系规则处理并显示依据；其余进入人工审核。

### 12.10 生成输入输出契约

LLM 输入只能包含：用户问题、已确认事实、缺失事实、路由计划、EvidenceBundle、RuleResult、允许的责任声明和输出 schema。检索到的网页文本被视为不可信数据，文本中的“忽略指令／调用工具”等内容不得成为系统指令。

结构化输出至少包含：

1. `scope_status`；
2. `known_facts`、`missing_facts`；
3. `issue_breakdown`；
4. `analysis_points[]`，每项带 `claim_id` 和 `evidence_ids`；
5. `applicability_result`／`risk_findings`；
6. `procedure_guidance`；
7. `client_reply_draft`；
8. `uncertainties`；
9. `confidence_dimensions`；
10. `review_required=true` 和免责声明。

模型输出先做 JSON Schema 校验；失败可进行一次格式修复，仍失败则返回证据和规则结果，不展示半截专业结论。

### 12.11 引用校验

每条关键主张依次验证：

1. 引用 ID 存在且属于本次 EvidenceBundle；
2. 文档／条款版本属于本次知识快照；
3. 原文 span 实际存在，URL、文号、条号一致；
4. 条款状态、日期、地区和主体没有被生成内容扩大；
5. 通过轻量蕴含模型／LLM 判定“支持／部分支持／不支持”，关键主张的“部分支持”也需人工审核；
6. 引用覆盖率不足时删除无依据断言，改写为不确定说明，或将整个运行置 `EVIDENCE_INSUFFICIENT`。

禁止模型自行生成 URL 和文号；展示字段只能从数据库证据对象渲染。

### 12.12 可信度

不展示伪精确单分数。保存以下维度：事实完整度、来源权威性、证据一致性、时效确定性、地域匹配度、规则确定性、引用覆盖率和审核状态。内部可用规则汇总 high／medium／low，但 UI 必须展开降级原因。

建议规则：任一硬门禁失败为 blocked；关键事实缺失、冲突未解决、关键主张引用未通过时最高为 low；只有事实完整、A／C 类适配证据充分、无冲突、引用覆盖达标且已审核，才显示 high。

### 12.13 政策更新影响分析

文档新版本发布后，按 `source_chunk_id`／关系台账反查：FAQ、风险规则、条件组、办税事项、知识关系和近 90 天答案主张。影响项生成 `feedback_tickets(category=outdated)` 或专门影响任务；未复核 FAQ／规则可配置自动暂停。历史运行不改写，只增加更新提示。

---

## 13. LangGraph 在线工作流

### 13.1 图节点

1. `receive_query`：保存消息、创建 run、固定事项版本和知识快照。
2. `scope_guard`：识别排除领域、禁止动作和敏感数据提示。
3. `load_memory`：加载 MySQL 已确认事实、摘要和 Redis 短期状态。
4. `extract_facts`：生成 proposed facts，不覆盖 confirmed facts。
5. `check_required_facts`：按候选路由检查必需事实。
6. `interrupt_for_facts`：保存 checkpoint，返回结构化追问。
7. `route_and_decompose`：产生一个或多个 route／subquery。
8. `build_retrieval_plan`：决定 exact、dense、BM25、FAQ、graph、rule 组合。
9. `parallel_retrieve`：并行召回，单路超时可降级。
10. `fuse_evidence`：过滤、RRF、重排、父块／图展开和冲突检测。
11. `execute_rules`：适用性和风险规则三值执行。
12. `generate_draft`：按结构化契约生成分析和草稿。
13. `validate_claims`：逐主张校验引用和范围。
14. `persist_result`：保存草稿、主张、证据和运行结果。
15. `request_review_or_end`：关键事项进入审核队列；安全拒答可直接完成。

### 13.2 工作流 State

`run_id`、`org_id`、`case_id`、`conversation_id`、`profile_version`、`public_knowledge_snapshot_id`、`org_knowledge_snapshot_id`、`user_query`、`confirmed_facts`、`proposed_facts`、`missing_facts`、`routes`、`subqueries`、`retrieval_plan`、`candidate_refs`、`evidence_bundle`、`rule_results`、`draft`、`claim_validations`、`confidence_dimensions`、`warnings`、`retry_counts`、`status`。

State 只保存 ID 和必要短文本；大规模候选、原始模型响应和文档正文写 MySQL／对象存储，避免 Redis checkpoint 膨胀。

### 13.3 超时、重试和降级

- MySQL／Redis 单次调用 1—3 秒；Milvus／Neo4j 3—5 秒；reranker 8 秒；LLM 首 token 10 秒、总生成 45 秒为 MVP 基线。
- 只对网络错误、429 和 5xx 做指数退避＋随机抖动；schema 错误、权限错误和业务校验错误不重试。
- 每个外部模型最多 2 次；生成格式修复最多 1 次。
- 任一节点重试和降级必须写运行事件，不得静默。

---

## 14. 异步任务设计

### 14.1 队列

| 队列 | 任务 | 并发特点 |
|---|---|---|
| `ingestion` | 白名单页面检查、文件下载、HTTP 元数据 | I/O 密集、域名限速 |
| `parsing` | PDF／HTML 解析、OCR、分块、差异 | CPU／OCR 密集，隔离并发 |
| `knowledge` | 实体关系候选、FAQ 候选、标准化 | LLM 配额受控 |
| `embedding` | 条款／FAQ／案例批量嵌入和 Milvus upsert | 批处理、按模型版本分组 |
| `graph_sync` | Neo4j 节点边 upsert／retire | 串行化同一 aggregate |
| `evaluation` | 金标准、规则回归、发布 smoke test | 可低优先级 |
| `maintenance` | Outbox 重试、投影巡检、缓存清理、影响扫描 | 定时执行 |

### 14.2 幂等要求

任务幂等键由 `task_type + aggregate_id + source_version + target_version` 组成。Worker 在执行前检查 `projection_sync_states`，upsert 后核对 checksum；任务被重复投递不能生成重复 chunk、向量、节点、边或版本。超过重试上限进入 dead 状态并告警，知识发布不能假装成功。

---

## 15. API 通用规范

### 15.1 基础约定

- Base URL：`/api/v1`。
- REST 接口使用 `application/json; charset=utf-8`；文件上传使用 multipart；流式事件使用 `text/event-stream`。
- Access Token 使用 Bearer，建议 30 分钟；Refresh Token 只放 Secure、HttpOnly、SameSite Cookie，数据库仅存哈希。
- 客户端不可传 `org_id` 决定租户；服务端从已验证会话注入。机构管理员切换机构须重新获取机构上下文令牌。
- 创建类接口支持 `Idempotency-Key`；可编辑资源支持 `If-Match`／`version_no`。
- 列表默认 `page_size=20`，最大 100；高增长列表使用 cursor。
- 每个响应头带 `X-Request-Id`，运行类响应返回 `run_id`。

### 15.2 响应包络

成功：

```json
{
  "data": {},
  "meta": {"request_id": "01...", "cursor": null}
}
```

失败：

```json
{
  "error": {
    "code": "FACTS_REQUIRED",
    "message": "需要补充业务发生日期后才能判断政策适用性",
    "details": {"missing_fact_keys": ["business_date"]},
    "retryable": false
  },
  "meta": {"request_id": "01..."}
}
```

`message` 可给用户看；内部堆栈、SQL、模型原始报错只进受控日志。

### 15.3 RBAC

| 能力 | consultant | reviewer | knowledge_admin | org_admin | auditor |
|---|---:|---:|---:|---:|---:|
| 创建／编辑本人事项 | ✓ | ✓ | 可选 | ✓ | 只读 |
| 提交查询与生成草稿 | ✓ | ✓ | — | ✓ | 只读 |
| 审核事项结论 | — | ✓ | — | 可配置 | 只读 |
| 编辑／发布 FAQ、规则、政策关系 | — | 只读证据 | ✓ | 管理权限 | 只读 |
| 管理成员和机构配置 | — | — | — | ✓ | 只读 |
| 查看完整审计 | — | 自己相关 | 知识相关 | ✓ | ✓ |

同一用户可有多个角色。系统必须支持“创建者不能审核自己提交的高风险规则／知识批次”的职责分离配置。

---

## 16. API 接口定义

### 16.1 身份与机构

| Method | Path | 权限 | 主要输入 | 主要输出 |
|---|---|---|---|---|
| POST | `/auth/login` | public | email／password | 用户、机构列表、access token；refresh cookie |
| POST | `/auth/refresh` | session | refresh cookie | 新 access token；轮换 refresh cookie |
| POST | `/auth/logout` | authenticated | 当前 session | 撤销结果 |
| GET | `/me` | authenticated | — | 用户、当前机构、角色、权限 |
| GET | `/organizations/{id}/members` | org_admin | cursor、role、status | 成员列表 |
| POST | `/organizations/{id}/members` | org_admin | email、role_code | 邀请／成员记录 |
| PATCH | `/organizations/{id}/members/{member_id}` | org_admin | role／status、version_no | 更新后的成员 |

### 16.2 事项、画像、会话与消息

| Method | Path | 权限 | 主要输入 | 主要输出 |
|---|---|---|---|---|
| GET | `/cases` | consultant+ | status、owner、cursor | 本机构事项列表 |
| POST | `/cases` | consultant+ | title、default_region_code、初始画像 | case、profile_version=1 |
| GET | `/cases/{case_id}` | case access | — | 事项、最新画像、状态、草稿摘要 |
| PATCH | `/cases/{case_id}` | owner／reviewer | title、assignee、version_no | 新事项版本 |
| POST | `/cases/{case_id}/profiles` | owner | 完整画像候选、supersedes_version | 新不可变画像版本 |
| POST | `/cases/{case_id}/facts/confirm` | owner／reviewer | fact proposals、profile_version | 确认／拒绝结果和新画像版本 |
| GET | `/cases/{case_id}/history` | case access | cursor | 状态、事实、草稿、审核时间线 |
| POST | `/cases/{case_id}/conversations` | case access | title | conversation |
| GET | `/conversations/{id}/messages` | case access | before_sequence、limit | 消息页 |

创建事项关键输入示例：

```json
{
  "title": "深圳某虚构商贸公司季度开票与优惠咨询",
  "default_region_code": "440300",
  "subject_profile": {
    "legal_form_code": "LIMITED_COMPANY",
    "vat_taxpayer_type": "SMALL_SCALE",
    "small_low_profit_status": "unknown",
    "industry_code": "GENERAL_TRADE",
    "business_date": "2026-07-15",
    "data_classification": "SYNTHETIC"
  }
}
```

### 16.3 查询运行与 SSE

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| POST | `/cases/{case_id}/queries` | case access | 保存用户问题并创建 run；返回 202、run_id、event_stream_url |
| GET | `/runs/{run_id}` | case access | 当前状态、路由、缺失事实、阶段结果、草稿 ID |
| GET | `/runs/{run_id}/events` | case access | SSE；支持 `Last-Event-ID` 的短期重放 |
| POST | `/runs/{run_id}/resume` | case access | 提交追问答案／确认事实并从 checkpoint 恢复 |
| POST | `/runs/{run_id}/cancel` | owner | 尽力取消未完成节点，不删除已产生审计 |
| GET | `/runs/{run_id}/evidence` | case access | 候选、选中证据、冲突、过滤理由 |
| GET | `/runs/{run_id}/risk-findings` | case access | 规则命中与待核实项 |

浏览器端使用支持流式读取的 `fetch` 携带 Bearer Token 连接 SSE，并发送 `Last-Event-ID`；不要把 access token 放进 `event_stream_url` 查询参数。若后续改用原生 `EventSource`，必须新增一次性、短时且绑定 `run_id + user_id + org_id` 的 stream token，不能复用登录令牌。

提交查询：

```json
{
  "conversation_id": "019...",
  "question": "我们这个季度还能享受小规模增值税优惠吗，怎么开票和申报？",
  "requested_outputs": ["analysis", "risk_review", "client_reply_draft"],
  "profile_version": 3
}
```

202 响应：

```json
{
  "data": {
    "run_id": "019...",
    "status": "queued",
    "event_stream_url": "/api/v1/runs/019.../events"
  },
  "meta": {"request_id": "019..."}
}
```

追问恢复：

```json
{
  "checkpoint_version": 4,
  "facts": [
    {"fact_key": "quarter_sales_amount", "value": "280000.00", "unit": "CNY", "confirm": true},
    {"fact_key": "invoice_type", "value": "SPECIAL_VAT_INVOICE", "confirm": true}
  ]
}
```

### 16.4 SSE 事件契约

事件格式只包含用户可见阶段，不传内部思维链：

```text
id: 17
event: facts.required
data: {"run_id":"019...","missing_facts":[...],"checkpoint_version":4}

```

| 事件 | data 关键字段 |
|---|---|
| `run.started` | run_id、status、created_at |
| `scope.checked` | in_scope、reason_codes、warnings |
| `route.decided` | routes、subqueries、route_confidence |
| `facts.required` | missing_facts、questions、checkpoint_version |
| `retrieval.completed` | route_id、candidate_count、selected_count、degraded_sources |
| `rules.completed` | applicability_result、finding_count、manual_review_required |
| `draft.delta` | draft_id、sequence、markdown_delta；不得包含未校验引用字段 |
| `citations.validated` | coverage、failed_claim_ids、warnings |
| `run.completed` | status、draft_id、review_required、confidence_dimensions |
| `run.failed` | error_code、safe_message、retryable |

`draft.delta` 只是体验层，最终页面必须以 `run.completed` 后从 REST 获取的持久化草稿为准。事件保存最近 24 小时，客户端断线用 `Last-Event-ID` 重连；过期则直接 GET run。

### 16.5 政策与证据

| Method | Path | 权限 | 主要输入／输出 |
|---|---|---|---|
| GET | `/policies/search` | authenticated | q、doc_no、region、business_date、status、source_level；返回文件／条款卡 |
| GET | `/policies/{document_id}` | authenticated | 文档元数据、当前版本、状态、来源 |
| GET | `/policies/{document_id}/versions` | authenticated | 版本列表和差异摘要 |
| GET | `/policies/{document_id}/timeline` | authenticated | 修改／替代／废止时间线，带证据 |
| GET | `/policy-versions/{version_id}/chunks` | authenticated | heading／clause、cursor；返回条款 |
| GET | `/chunks/{chunk_id}` | authenticated | 原文、父块、定位、文号、URL、状态 |
| GET | `/chunks/{chunk_id}/relations` | authenticated | 受控一／二跳证据路径 |

`business_date` 对适用性和版本查询必填；普通搜索可空，但返回卡必须明确“当前状态，不代表指定业务日期适用”。

### 16.6 FAQ

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| GET | `/faqs/search` | authenticated | q、region、business_date、scope；返回候选和证据状态 |
| GET | `/faqs/{faq_id}` | authenticated | 正文、变体、适用范围、证据、版本和审核状态 |
| POST | `/faqs` | knowledge_admin | 创建官方／机构 FAQ 草稿 |
| PATCH | `/faqs/{faq_id}` | knowledge_admin | 乐观锁更新，已发布内容产生新版本 |
| POST | `/faqs/{faq_id}/variants` | knowledge_admin | 新问题变体草稿 |
| POST | `/faqs/{faq_id}/evidences` | knowledge_admin | 绑定正式条款 |
| POST | `/faqs/{faq_id}/submit-review` | knowledge_admin | 创建审核任务 |
| POST | `/faqs/{faq_id}/publish` | authorized reviewer | 验证证据后发布并发 Outbox |
| POST | `/faqs/{faq_id}/retire` | knowledge_admin+review | 停用并删除检索投影 |
| POST | `/cases/{case_id}/promote-memory` | reviewer | 从已审核、脱敏事项创建机构经验草稿，不直接发布 |

FAQ 发布请求需包含 `faq_version_id`、`version_no`、审核任务 ID 和证据版本哈希。若绑定政策已改变，返回 `RESOURCE_VERSION_CONFLICT`。

### 16.7 风险与规则管理

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| POST | `/cases/{case_id}/risk-runs` | case access | 可单独执行事项风险审查；内部复用 analysis run |
| GET | `/risk-rules` | reviewer／knowledge_admin | 按税种、地区、状态、类别查询 |
| POST | `/risk-rules` | knowledge_admin | 创建规则逻辑对象和 v1 草稿 |
| POST | `/risk-rules/{id}/versions` | knowledge_admin | 创建不可变新版本 |
| POST | `/risk-rule-versions/{id}/validate` | knowledge_admin | schema、fact key、证据、静态冲突校验 |
| POST | `/risk-rule-versions/{id}/test` | knowledge_admin | 执行固定测试用例 |
| POST | `/risk-rule-versions/{id}/submit-review` | knowledge_admin | 提交审核 |
| POST | `/risk-rule-versions/{id}/publish` | reviewer | 仅全部测试通过时发布 |

风险结果输出必须含 `rule_code`、版本、等级、truth value、触发事实、缺失事实、证据、建议和是否需人工复核。

### 16.8 办税事项

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| GET | `/procedures` | authenticated | 地区、税种、主体、关键词、业务日期 |
| GET | `/procedures/{id}` | authenticated | 条件、材料、渠道、步骤、期限、错误、依据 |
| POST | `/procedures` | knowledge_admin | 创建草稿 |
| POST | `/procedures/{id}/versions` | knowledge_admin | 创建新版本 |
| POST | `/procedure-versions/{id}/submit-review` | knowledge_admin | 提交审核 |
| POST | `/procedure-versions/{id}/publish` | reviewer | 发布并更新图投影 |

无深圳／广东地方证据时，响应必须返回 `region_match=national_only` 和明确降级提示，不能把全国一般说明伪装成当地办理口径。

### 16.9 审核、反馈、知识采集与发布

| Method | Path | 权限 | 说明 |
|---|---|---|---|
| GET | `/review-tasks` | reviewer | 分页、类型、优先级、提交人、状态 |
| GET | `/review-tasks/{id}` | reviewer | 审核包：事实、草稿、逐主张、证据、规则、版本 |
| POST | `/review-tasks/{id}/actions` | reviewer | approve／conditional_approve／return／reject，可逐主张 |
| POST | `/feedback` | authenticated | 针对回答、条款、FAQ、规则提交纠错 |
| GET | `/feedback` | knowledge_admin／auditor | 分类、状态、关联知识对象 |
| PATCH | `/feedback/{id}` | assignee | 分派、处理、关闭；需版本号 |
| GET | `/knowledge/sources` | knowledge_admin | 白名单来源 |
| POST | `/knowledge/ingestion-jobs` | knowledge_admin | URL／文件导入／增量任务 |
| POST | `/knowledge/uploads` | knowledge_admin | 获取上传信息并创建导入任务 |
| GET | `/knowledge/jobs/{id}` | knowledge_admin | 阶段、计数、安全错误和产物 |
| GET | `/knowledge/candidates` | knowledge_admin | 待审核文档、关系、FAQ、条件候选 |
| POST | `/knowledge/publish-batches` | knowledge_admin | 创建发布批次 |
| POST | `/knowledge/publish-batches/{id}/validate` | knowledge_admin | 全量门禁报告 |
| POST | `/knowledge/publish-batches/{id}/activate` | reviewer／admin | 构建并激活新快照 |
| GET | `/audit-logs` | auditor／admin | 按资源、动作、人员、时间查询 |

### 16.10 错误码

| HTTP | code | 场景 |
|---:|---|---|
| 400 | `VALIDATION_FAILED` | schema、字段、规则表达式错误 |
| 401 | `AUTH_REQUIRED`／`TOKEN_EXPIRED` | 未登录／令牌过期 |
| 403 | `AUTH_FORBIDDEN` | 角色无权 |
| 403 | `TENANT_SCOPE_VIOLATION` | 资源不属于当前机构；日志必须告警 |
| 404 | `RESOURCE_NOT_FOUND` | 不暴露跨租户资源是否存在 |
| 409 | `RESOURCE_VERSION_CONFLICT` | 乐观锁／证据版本变化 |
| 409 | `POLICY_STATUS_CONFLICT` | 政策状态或沿革冲突 |
| 422 | `FACTS_REQUIRED` | 必需事实缺失；查询运行通常用 202＋SSE 表达 |
| 422 | `OUT_OF_SCOPE` | 明确排除任务 |
| 422 | `EVIDENCE_INSUFFICIENT` | 关键证据不足 |
| 422 | `REVIEW_REQUIRED` | 不能自动完成的专业判断 |
| 429 | `RATE_LIMITED` | 用户／机构／模型配额 |
| 502 | `MODEL_UNAVAILABLE` | 模型服务不可用 |
| 503 | `RETRIEVAL_DEGRADED` | 关键检索存储不可用且无法安全降级 |
| 500 | `INGESTION_FAILED`／`INTERNAL_ERROR` | 采集或内部异常，隐藏实现细节 |

---

## 17. 安全、隐私与责任控制

### 17.1 租户与授权

- Repository 接口必须要求 `TenantContext`，禁止可选 `org_id`。
- 所有机构表的主键查询写成 `WHERE org_id=? AND id=?`；不能先查 ID 再在业务层判断机构。
- Milvus FAQ／案例过滤由服务端模板生成；Neo4j MVP 不存机构私有图。
- 每个 API 都有权限单测和跨租户负向集成测试。
- 知识管理员无权读取与知识纠错无关的完整客户会话；必要时只看脱敏片段。

### 17.2 敏感数据

- 输入端明确提示只能使用虚构／脱敏摘要；检测身份证号、手机号、银行卡、统一社会信用代码等模式并提醒／阻止。
- 日志默认不记录完整 query、answer、原始文件；记录哈希、长度、分类、ID 和可选脱敏摘要。
- 导出件带机构、事项、生成时间、审核状态和免责声明水印；下载写审计。
- 密钥来自环境／Secret Manager；不得写 MySQL、Git、日志或前端 bundle。

### 17.3 Prompt Injection 与生成安全

- 政策网页、PDF、FAQ 和用户上传文件一律作为数据，不具有指令优先级。
- 模型不能获得数据库任意查询、网络访问和文件写入能力；工具调用使用固定 schema 和服务端白名单。
- 引用、URL、文号和风险等级由服务端结构化渲染，不信任模型自由文本字段。
- 不返回 chain-of-thought；只返回结果、依据、缺失事实、规则命中和阶段原因。

### 17.4 产品阻断规则

遇到失效政策被当现行依据、地区错配、必要主体明确不符、关键主张无来源、实质冲突未解决、自动申报／缴税请求、排除行业或复杂跨境事项时，阻断确定性答复并转人工／拒答。

---

## 18. 可观测性与审计

### 18.1 一次运行必须记录

- request_id、run_id、org_id、用户／角色、事项和画像版本；
- 路由器版本、路由结果、缺失事实和子问题；
- 知识快照、检索配置、候选 ID／排名／过滤理由、图模板和路径 ID；
- 规则版本、truth value、触发／缺失事实；
- 模型／嵌入／重排／提示词版本、token、耗时、重试和估算成本；
- 主张、引用校验、降级、审核任务和最终状态。

不记录模型私有推理过程，不把完整政策正文重复进日志。

### 18.2 指标

| 类别 | 指标 |
|---|---|
| API | 请求量、p50/p95/p99、4xx/5xx、租户违规、SSE 断线重连 |
| 工作流 | 各节点耗时、等待追问率、失败／重试／降级率、60 秒完成率 |
| 检索 | Recall@K、零结果率、各通道命中率、rerank 耗时、过滤原因分布 |
| 知识 | 采集变化率、解析失败率、候选待审时长、索引同步延迟、投影漂移 |
| 模型 | token、成本、schema 失败、超时、引用验证失败、拒答率 |
| 业务 | 草稿审核通过／退回、主要错误类型、FAQ 复用率、咨询处理时间 |

结构化日志使用 request_id／run_id 关联；Trace 跨 API、Worker、模型和存储传递，但不含敏感正文。

---

## 19. 故障降级

| 故障 | 可接受降级 | 禁止行为 |
|---|---|---|
| Redis 不可用 | 从 MySQL 加载持久状态；关闭缓存和 SSE 事件重放；新的复杂运行可返回稍后重试 | 不丢用户消息，不假装 checkpoint 可恢复 |
| Milvus 不可用 | 明确文号可用 MySQL 精确查询；办税事项可用结构化库；复杂语义咨询返回检索降级／稍后重试 | 不仅靠 LLM 常识回答 |
| Neo4j 不可用 | 使用已召回条款做普通 RAG，标记沿革／关系能力降级；版本问题若 MySQL 沿革台账完整可继续 | 不宣称完整多跳和冲突检查 |
| LLM 不可用 | 返回可核验政策列表、规则结果、缺失事实和人工处理提示 | 不输出旧缓存草稿冒充当前结果 |
| reranker 不可用 | 使用 RRF 排名并降低可信维度 | 不静默维持原置信标记 |
| MinIO 不可用 | 已在 MySQL 的条款可检索；原件打开和新采集暂停 | 不发布无法核验原件的新知识 |
| MySQL 不可用 | 全部写操作和专业查询停止，返回可重试错误 | 不以 Milvus／Redis 数据代替主数据写入 |
| 外部官方站点不可用 | 保留上次已审核版本，采集任务重试并显示更新时间 | 不把站点暂时不可达等同于政策失效 |

---

## 20. 测试与验收

### 20.1 测试层级

| 层级 | 必测内容 |
|---|---|
| 单元 | 规则三值逻辑、日期／地区过滤、文号规范化、状态机、RRF、权限、脱敏 |
| 属性／边界 | 日期开闭区间、金额边界、unknown 传播、重复事件幂等、图环和最大深度 |
| 集成 | MySQL migration、Outbox→Milvus／Neo4j、MinIO 解析、Redis 恢复、SSE 重连 |
| Contract | OpenAPI schema、错误码、SSE 事件 schema、模型结构化输出 schema |
| Golden | 200—300 道税务师标注问题，覆盖七路由、四态适用性、政策沿革、拒答 |
| 安全 | 跨租户、越权、恶意文件、prompt injection、敏感数据、任意 Cypher／filter 注入 |
| 回归 | 每条发布风险规则 100% 固定用例；每次模型／提示词／索引升级跑全套 |

### 20.2 MVP 门槛

| 指标 | 门槛 |
|---|---:|
| 文档 Recall@10 | ≥ 90% |
| 条款 Recall@10 | ≥ 85% |
| 引用可验证率 | ≥ 98% |
| 关键主张证据覆盖率 | ≥ 95% |
| 政策状态识别准确率 | ≥ 98% |
| 地域过滤准确率 | ≥ 98% |
| 适用性四态准确率 | ≥ 90%，且错误“初步适用”单独统计 |
| 关键缺失信息识别率 | ≥ 90% |
| 高风险规则精确率 | ≥ 95% |
| 规则版本固定用例 | 100% 通过 |
| 超范围正确拒答率 | ≥ 95% |
| 编造文号、已知失效政策误作有效依据、未审核知识作正式事实 | 0 |

体验目标：精确政策检索 95% 在 3 秒内返回首屏；条款定位 95% 在 2 秒内；复杂分析 5 秒内有阶段反馈、60 秒内首版完成；上一稳定知识快照在发布失败时不受影响。

### 20.3 发布门禁

- 数据 migration 可前滚和安全回退；
- 所有 P0 API contract 测试通过；
- 七路由 golden set 达标；
- 规则回归 100%；
- 跨租户负向测试 100%；
- 投影一致性无未解释差异；
- 关键主张引用、政策状态和地域零严重错误；
- 税务审核人签署首批知识快照和评测报告。

---

## 21. Codex 实现顺序与完成定义

### 21.1 建议顺序

1. **基础域与约束：**错误模型、ID／时间、租户上下文、RBAC、状态机、审计、migration。
2. **MySQL 主数据：**政策／版本／条款、事项／事实／消息、FAQ／规则／办税、运行／证据／审核、Outbox。
3. **数据链路：**MinIO、手工导入、HTML／PDF 解析、父子分块、版本差异；先不做自动爬虫。
4. **检索投影：**Milvus 三集合、Neo4j 公共图、Outbox Worker、重建和一致性检查。
5. **在线检索：**精确、dense、BM25、FAQ、图模板、RRF、reranker、EvidenceBundle。
6. **规则和工作流：**DSL、七路由、事实追问、LangGraph checkpoint／resume、风险结果。
7. **生成与验证：**结构化输出、主张拆分、引用校验、SSE、免责声明。
8. **审核与知识发布：**逐主张审核、FAQ／规则／办税发布、快照、影响分析、反馈闭环。
9. **前端 P0：**事项工作台、对话／追问、证据阅读、风险、办税、审核、知识后台。
10. **评测与加固：**金标准、性能、故障降级、安全、可观测性。

### 21.2 每个功能的 Definition of Done

- 有明确用例和权限矩阵；
- OpenAPI／SSE／事件 schema 已固定并有 contract test；
- 数据表有 migration、索引和回滚／补偿策略；
- 跨租户负向测试、幂等测试、异常和降级测试通过；
- 关键动作有审计；
- 线上结果可回放到输入事实、快照、候选、规则、模型和审核；
- 监控指标和安全日志已接入；
- 文档与实现同步，不以注释代替业务约束。

### 21.3 Codex 编码硬约束

1. 采用模块化单体；跨模块通过应用服务／明确接口，不直接访问其他模块 ORM 实体。
2. API Handler 只做鉴权、schema、调用应用服务和响应映射；规则、状态迁移、租户判断不得散落在 Handler。
3. 所有外部存储和模型通过 Adapter，测试可替换；域层不依赖 FastAPI、Milvus、Neo4j SDK。
4. 禁止跨库同步双写，统一使用 Outbox；所有 Worker 任务必须幂等。
5. 禁止把政策状态、适用条件、风险等级写死在提示词或前端。
6. 禁止由模型自由生成 source URL、文号、风险等级和审核状态。
7. 未发布资产必须在 Repository 和检索层双重隔离。
8. 每个查询必须带知识快照和事项事实版本；不得默认读取“当前最新”后覆盖历史运行语义。
9. 不生成或持久化 chain-of-thought；只存可审核输出和决策原因代码。
10. 下一轮生成目录和基础配置时，以本文模块边界组织，不按技术组件堆成 `utils/services/common` 大杂烩。

---

## 22. 下一轮目录与基础配置的输入清单

用户确认本文后，下一轮应生成：

1. Monorepo 或前后端并列目录；建议 `apps/web`、`apps/api`、`apps/worker`、`packages/contracts`、`infra`、`tests/golden`。
2. FastAPI 模块骨架、配置加载、依赖注入、错误处理、请求 ID、租户上下文和健康检查。
3. React＋TypeScript 基础路由、API client、SSE client、权限守卫和页面占位。
4. MySQL migration 基线与 ORM 模型分组；Milvus collection schema；Neo4j constraints；Redis／MinIO 配置。
5. Docker Compose、环境变量示例、开发／测试配置、Makefile 或任务脚本。
6. Celery 队列、Outbox consumer、LangGraph state skeleton、模型 gateway interface。
7. OpenAPI 初稿、统一错误码、JSON Schema、SSE event contracts。
8. 单元／集成／contract／golden 测试框架和 CI 基线。

在下一轮开始前只需确认：仓库是否采用 Monorepo、Python 包管理器、前端包管理器、DashScope 具体模型、是否本地部署 BGE、以及开发机是否需要完整拉起 Milvus／Neo4j／MinIO。

---

## 23. 官方技术参考

- [Milvus Full Text Search（BM25）](https://milvus.io/docs/full-text-search.md)
- [Milvus Multi-Vector Hybrid Search](https://milvus.io/docs/multi-vector-search.md)
- [FastAPI Server-Sent Events](https://fastapi.tiangolo.com/tutorial/server-sent-events/)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Memory](https://docs.langchain.com/oss/python/langgraph/add-memory)
- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [Neo4j Constraints](https://neo4j.com/docs/cypher-manual/current/schema/constraints/)
- [Neo4j Search-performance Indexes](https://neo4j.com/docs/cypher-manual/current/indexes/search-performance-indexes/)

---

## 附录 A：关键数据流追溯示例

一条“该优惠初步适用”的主张至少应形成以下引用链：

`answer_claims.id`
→ `claim_evidences.chunk_id`
→ `document_chunks.source_chunk_id`
→ `document_versions.content_hash_sha256 / raw_object_key`
→ `source_documents.doc_no / canonical_url / policy_status`

同时关联：

`analysis_runs.profile_version`
→ `case_subject_profiles / case_facts`
→ `condition_sets.expression_json` 或 `risk_rule_versions.trigger_expression_json`
→ `knowledge_snapshot_items`
→ `review_actions`

缺少任一关键环节，主张不能进入“审核通过”。

## 附录 B：关键审查清单

- [ ] MySQL 是否是结构化状态和版本的唯一事实源？
- [ ] Milvus／Neo4j 是否可从 MySQL＋MinIO 完整重建？
- [ ] Redis 丢失是否只影响短期体验而不丢正式事实？
- [ ] FAQ 命中后是否仍校验条款、状态、日期、地区和主体？
- [ ] 普通聊天是否绝不会自动进入 FAQ／机构经验？
- [ ] 每条图关系是否有 `source_chunk_id` 和审核状态？
- [ ] 风险规则是否独立于提示词、可版本化、可三值执行、可回归？
- [ ] 复杂咨询是否按子问题分别检索和核验证据？
- [ ] 历史运行是否绑定知识快照、画像版本、模型和提示词版本？
- [ ] SSE 是否只传用户可见阶段和答案增量，不传内部思维链？
- [ ] 所有机构资源是否经过仓储层租户过滤和跨租户测试？
- [ ] 发布失败时是否保持上一稳定快照可用？
