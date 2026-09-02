# Changelog

## 2026-09-02 - 已确认官方小样本资料下载

- 用户确认后，新增版本化来源清单与低频下载工具；工具限制为清单内 HTTPS URL，校验格式与大小，记录下载时间、URL、MIME、SHA-256 和安全失败摘要，原件留在 Git 忽略的本地目录。
- 已成功下载并解析预检国家级 HTML、国家级 PDF 和广东 PDF；深圳市政府确认 URL 因本机 TLS `BAD_ECPOINT` 下载失败，未替换来源、未导入、未发布。
- 新增操作手册，明确成功资料后续必须走来源登记、受控上传、候选审核、发布批次和快照门禁；当前 PDF 解析各只得到一个块，尚不能宣称分块质量或检索验收通过。

影响模块：Official Sample Manifest、Controlled Download Utility、Local Sample Runbook。

## 2026-09-02 - 工作台查询运行 SSE 重放

- 新增 `analysis_run_events` 及 Alembic `20260902_0013`：运行状态、补充事实、失败安全摘要、最终回答增量和完成状态均以单调序号持久化，可按 `Last-Event-ID` 重放。
- 新增受认证的 `GET /api/v1/query-runs/{run_id}/events` SSE 接口；只返回已持久化的安全载荷，事件中不保存或发送 Prompt、密钥、私有推理或思维链。
- 工作台通过带 Bearer 请求头的 `fetch` 流读取事件，断开后携带事件游标重连，并用受认证的运行读取接口对账最终状态。为避免令牌进入 URL，未采用原生 `EventSource`。

影响模块：Query Run Event、MySQL Migration、SSE OpenAPI Contract、Web Cases Workspace。

验证限制：事件迁移已完成离线 SQL 生成；Docker Desktop daemon 当时不可连接，尚未进行真实 MySQL 升降级与运行中断重连验证。

## 2026-09-02 - 工作台查询运行与最终回答持久化

- 新增 `analysis_runs` 主数据表及迁移：运行固定记录事项事实、知识快照、检索计划、规则版本、证据 ID、状态、错误安全摘要和最终回答消息关联。
- 查询提交改为会话内的原子写入：用户问题与运行记录同事务保存；资料不足时进入 `needs_input`，缺少激活公共知识快照时安全失败，资料完整时仅进入 `queued`，不伪造模型完成。
- 受信任执行器可将最终回答、引用、信息缺口和助手消息同事务写入；引用必须属于本次证据清单，私有推理不保存也不对外返回。
- 工作台接入运行读取契约与状态、证据、缺口、错误和已持久化最终回答展示；真实模式须先创建会话并填写匿名化问题。

影响模块：Query Run、Conversation Message、Knowledge Snapshot Resolver、MySQL Migration、OpenAPI Contract、Web Cases Workspace。

## 2026-09-02 - 工作台会话软删除与恢复

- 新增会话软删除和恢复接口；仅会话发起人或机构管理员可操作，并复用事项写权限和租户隔离校验。
- 已删除会话保留消息与审计记录，但禁止继续读取上下文、读取消息或追加消息；恢复后方可继续使用。
- 工作台为当前会话提供删除/恢复确认、状态反馈和已删除禁用态；预览模式仅使用虚构数据验证交互。

影响模块：Conversation API、Conversation Service、MySQL Migration、OpenAPI Contract、Web Cases Workspace。

## 2026-09-02 - 前端第 14 步受控资料导入接入

- 知识运营页接入既有本地资料导入接口，要求关联已登记来源、文件与必要政策元数据，并以 multipart 提交。
- 导入成功仅展示后端返回的任务状态和解析分块数；不实现外部资料下载、网页爬取或自动发布。

影响模块：Web Knowledge Operations、Web API Client。

## 2026-09-02 - 前端第 13 步知识来源登记接入

- 知识运营页接入既有白名单来源登记接口，登记成功后刷新来源列表；来源以草稿状态保存，保留服务端权限和重复域名校验。
- 页面明确限定为来源元数据登记，未接入下载、爬取、导入或后台任务触发。

影响模块：Web Knowledge Operations、Knowledge API Client。

## 2026-09-02 - 前端第 12 步知识候选单条审核接入

- 知识运营页接入既有候选审核接口；具备权限的正式会话可单条通过或退回候选，退回原因在前端和服务端均受最小长度约束。
- 审核成功后仅刷新候选列表；预览模式保持虚构数据和禁用操作，不伪造审核结论或发布状态。

影响模块：Web Knowledge Operations、Knowledge API Client。

## 2026-09-02 - 前端第 11 步成员设置接入

- 设置页接入当前成员上下文和机构成员列表；机构管理员可通过既有接口邀请成员、更新角色或启停状态，更新请求携带服务端版本号。
- 预览模式仅展示虚构成员，所有写操作禁用；成员读取、权限失败、空数据和操作失败均保留可理解反馈。

影响模块：Web Settings、Organization API Client。

## 2026-09-02 - 前端第 9 步设计稿最终验收

- 按已确认布局调整固定导航底部顺序：用户头像在左，设置入口在右；保持设置选中态和顶部页签语义。
- 已逐页复核设计基线中的 190px 左侧导航、蓝紫品牌色、浅灰目录页背景以及工作台、政策、办税、审核、知识、反馈、审计和设置的页面入口。

影响模块：Web App Frame、Web Final Visual Acceptance。

## 2026-09-02 - 前端第 8 步全局视觉回归

- 统一设置入口与主导航的选中态样式，并在顶部栏显示“设置 / 机构与成员”，保持固定导航、标题栏与页面内容的视觉语义一致。
- 在桌面浏览器逐页回归工作台、事项、政策、办税、审核、知识、反馈、审计和设置入口；不扩展后端 API 或伪造尚未接入的能力。

影响模块：Web App Frame、Web Visual Regression。

## 2026-09-02 - 前端第 7 步反馈、审计与设置空态

- 反馈纠错页调整为轻量提交与待处理列表双栏，保留后端反馈提交、重试和脱敏边界。
- 操作审计页改为脱敏摘要表格，不展示审计快照正文；设置入口新增明确的未接入 API 空态。

影响模块：Web Feedback、Web Audit、Web Settings Routing。

## 2026-09-02 - 前端第 6 步审核与知识运营

- 审核中心调整为待审核紧凑队列表，保留原有审核详情跳转及事实、规则缺口呈现。
- 新增 `/knowledge` 知识运营页：真实模式读取待审核候选与已登记来源，预览模式只展示虚构数据。
- 导入、批量审核、批次校验与快照物化需要额外文件、版本或发布批次上下文，当前明确禁用，不伪造操作成功。

影响模块：Web Review Queue、Web Knowledge Operations、Knowledge API Client。

## 2026-09-02 - 前端第 4 步事项管理

- 新增 `/cases/manage` 事项管理页，并统一接入固定左侧导航；页面复用已有事项列表接口，保留加载、空态、错误重试和登录权限边界。
- 事项行可进入工作台；新建入口复用工作台既有事项创建抽屉，不重复新增写接口。
- 预览模式仅使用虚构事项，服务端未提供的状态分组不展示虚构计数或筛选结论。

影响模块：Web Cases Management、Web Routing、App Navigation。

## 2026-09-02 - 前端第 5 步政策与办税目录

- 政策检索与办税事项页统一为轻量目录页：标题说明、紧凑筛选与结果列表按新版界面规范重排。
- 保留已有政策证据抽屉、地区回退提示、官方来源链接及办税事项的材料、渠道和有效期展示。
- 页面不伪造模型结论、办税执行状态或后端未返回的正式依据；预览数据继续明确标注为虚构。

影响模块：Web Policy Search、Web Procedures、Evidence Detail。

## 2026-09-01 - Stage 10 P0 金标准与验收基线

- 新增 P0 金标准回归：范围闸门、确定性风险命中与依据、查询审计不保存原始问题文本、审计 API Schema 脱敏，以及审计读取和反馈治理的权限隔离。
- 新增进程内范围闸门与确定性路由的一秒性能烟雾检查；不将其表述为外部检索或模型生成端到端性能结果。
- 新增 P0 演示与验收手册，记录虚构演示链路、自动化门禁、依赖降级与不可验证环境的如实报告规则。

影响模块：Golden Tests、P0 Runbook、Query Audit、Risk Rule、Audit Contract。

## 2026-09-01 - Stage 9 反馈与审计最小闭环

- 新增仅限 `audit:read` 的机构范围审计查询 API；响应只包含动作、资源、结果、请求 ID、时间与可选脱敏摘要，绝不返回审计前后 JSON、IP 或 User-Agent 哈希。
- 新增 `feedback_items` 及 Alembic `20260901_0010`：反馈关联事项/画像/可见资源和位置标识，状态限定为 `submitted`、`accepted`、`resolved`、`rejected`；解决反馈必须关联知识修订对象，且不能直接改写正式知识。
- 反馈提交、受理、解决、拒绝均使用版本号并发保护并追加审计；资源访问按机构与事项范围校验。
- 新增 `/audit` 与 `/feedback` 前端页面和虚构预览，包含空态、加载失败重试、权限失败文案与内部专业辅助提示。

影响模块：Audit、Feedback、Identity Permissions、API Contracts、Web Routing。

迁移与回滚：升级至 Alembic `20260901_0010` 新增 `feedback_items` 和索引；降级仅适用于确认无需保留反馈追溯的开发环境。审计日志保持追加式，不被迁移或应用回滚删除。

## 2026-08-31 - Stage 8 受控查询与确定性风险规则

- 新增白名单风险 DSL 与三值执行器，支持布尔组合和基础比较；缺失事实按规则声明映射为 `need_info`、`not_hit` 或 `manual_review`，风险等级只来自规则定义。
- 新增事项查询运行入口：先校验业务发生日和地区，再生成受控检索计划并执行已注入的规则；LLM 不参与风险命中、等级或规则结果变更。
- 查询运行在审计日志中关联运行 ID、事项画像版本、路由和追问事实键，不保存原始查询文本；当前运行状态保留在进程内，服务重启后状态查询会如实返回不存在。
- 新增查询 API 与事项工作台受控分析卡片；无已发布规则时明确显示不会由模型补造规则结论，预览模式仅展示虚构数据。
- 针对 Docker Desktop 上 etcd 的短暂磁盘同步停顿，增加可配置的开发环境心跳与选举容错窗口；不改变数据卷、代理或正式环境默认边界。

影响模块：Risk DSL、Query Orchestration、Audit、API Contracts、Web Cases Workspace。

迁移与回滚：无 MySQL 迁移；回滚应用代码不会删除已有审计记录。当前尚未接入已发布规则的持久化仓储或真实检索执行，后续接入必须保持规则版本与审核状态门禁。

## 2026-08-31 - Stage 6 阶段验收

- 以 MySQL Docker 集成链路验证：资料导入后的候选审核、发布批次、待激活快照、Outbox 状态、投影状态与激活审计可在同一受控流程回放。
- Milvus 与 Neo4j Adapter 分别以独立虚构样本完成实际 Docker 写入/读取验证；Worker 路由、MySQL 载荷读取、抽样校验及别名门禁由自动化测试覆盖。
- 不将虚构集合设为正式别名，不导入真实税务资料，不自动对外发布或激活未审核知识。

影响模块：Knowledge Projection、Worker Outbox、Milvus、Neo4j、Snapshot Activation、Integration Tests。

迁移与回滚：无 MySQL 迁移；本阶段代码回滚不会删除主数据或切换正式别名。

## 2026-08-31 - Stage 6.6 投影抽样校验与别名门禁

- 新增 Milvus 快照抽样校验器：从 MySQL 快照重建受控载荷，读取版本化集合中的样本条款并核对快照 ID。
- 仅校验通过才允许切换 `policy_chunks_current`；校验失败不会更改别名。
- 本步没有把现有虚构集合切换为正式别名，也不会绕过既有快照激活审核门禁。

影响模块：Milvus Projection Smoke Check、Versioned Alias Gate、Unit Tests。

迁移与回滚：无 MySQL 迁移；回滚不会改变当前别名或已激活快照。

## 2026-08-31 - Stage 6.5 Worker 快照投影执行

- Worker 从 MySQL 知识快照读取已审核候选及真实资料版本，构造带来源、校验和与快照 ID 的 Milvus 条款和 Neo4j 文档-条款关系载荷。
- Outbox 执行器按事件类型单向路由至对应 Adapter；开发环境仅在 `embedding_provider=fake` 时使用确定性开发向量，生产环境保持未配置执行端，避免把测试向量写入正式索引。
- MySQL 仍是唯一主数据源；不提供 API 直接投影、正式别名切换或自动激活。

影响模块：Worker Outbox、Knowledge Snapshot Projection Payload、Milvus/Neo4j Adapter、MySQL Integration Tests。

迁移与回滚：无 MySQL 迁移；回滚 Worker 接线不会删除 MySQL 快照或 Outbox 记录。

## 2026-08-31 - Stage 6.4 快照激活门禁

- 新增知识快照激活应用服务：仅具备 `knowledge:review` 权限的人员可请求激活仍处于 `pending_activation` 的快照。
- 激活前必须确认 Milvus 政策投影与 Neo4j 图谱投影均以同一快照清单版本成功同步，并执行可注入的受控抽样校验；任一条件不满足均保留待激活状态。
- 激活、审核人和激活时间在同一 MySQL 事务内写入，并记录 `knowledge.snapshot.activated` 审计事件；未提供 API 自动激活入口，也未切换 Milvus 别名。

影响模块：Backend Knowledge Snapshot Activation、Projection Sync State、Audit、MySQL Integration Tests。

迁移与回滚：无 MySQL 迁移；回滚应用逻辑不会自动改变已激活快照，需由后续受控版本切换流程处理。

## 2026-08-31 - Stage 6.3 Neo4j 关系投影

- 新增 Neo4j 图谱投影 Adapter，使用关系 ID 的 `MERGE` 保证重复投递不重复创建关系。
- 每条关系保留快照、来源条款、来源地址、关系类型和内容校验和；不接收客户端 Cypher。
- 已用本地 Neo4j 的独立 stage63 虚构关系验证写入和只读计数；未写入真实资料或激活快照。

## 2026-08-31 - Stage 6.2c 政策向量载荷对齐

- 政策投影契约新增固定测试向量字段；Adapter 将其映射为 Milvus `dense_vector` 写入载荷。
- 仍强制保留快照、来源、审核状态和内容校验和；不允许空向量进入投影契约。
- 正式版本化集合 bootstrap、索引与别名切换仍未执行。

## 2026-08-31 - Stage 6.2d 版本化集合 Bootstrap 验证

- 新增版本化 Milvus 政策集合 bootstrap：显式字符串主键长度、稠密向量字段和 AUTOINDEX/COSINE 索引，动态字段保留可追溯元数据。
- 已在独立 `policy_chunks_v1_stage62` 测试集合通过 Adapter 写入、flush、加载和主键读取虚构已审核条款；不使用正式别名、不激活快照。

## 2026-08-31 - Stage 6.2 Milvus 政策投影 Adapter

- 新增官方 pymilvus 客户端依赖与政策投影 Adapter；Adapter 只接收 6.1 的已审核、可溯源契约记录。
- 同一批写入必须属于一个快照，并随写入携带幂等键、条款/资料版本、地区、有效期、审核状态和内容校验和。
- 本步尚未创建集合、生成嵌入或把快照切换为 active；正式向量字段与检索入口留待后续步骤。

影响模块：Backend Milvus Projection Adapter、Dependencies、Unit Tests。

迁移与回滚：无 MySQL 迁移；回滚依赖和 Adapter 代码不会删除任何 MySQL 主数据或激活快照。

## 2026-08-31 - Stage 6.1 投影 Adapter 契约

- 新增 Milvus 政策条款与 Neo4j 关系投影的独立数据契约及可替换 Port；所有记录必须绑定快照、来源条款、来源地址和内容校验和。
- 契约拒绝非已发布条款、缺失来源或非法校验和；投影结果只描述投影状态，不包含或暗示快照激活。
- 本步不安装外部数据库 SDK、不执行外部写入，也不变更 MySQL 主数据或快照状态。

影响模块：Backend Projection Contracts、Knowledge Snapshot Boundary、Unit Tests。

迁移与回滚：无数据库迁移；回滚移除契约代码即可，既有 Outbox 和快照不受影响。

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
