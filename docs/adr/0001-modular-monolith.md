# ADR 0001：采用模块化单体与独立进程入口

- 状态：Accepted
- 日期：2026-08-30

API、Worker 和 Scheduler 使用同一个 Python 包与领域模型，通过不同入口部署。MVP 不拆后端微服务，
避免共享模型复制和分布式事务复杂度。业务模块仍通过公开 Service、Contract 或领域事件协作。