# ADR 0004：通过 Outbox 构建检索投影

- 状态：Accepted
- 日期：2026-08-30

业务变更和 Outbox 事件在同一 MySQL 事务中提交。Worker 幂等消费事件并更新 Milvus、Neo4j 等投影；
投影失败不回滚已提交业务事务，且不能将知识发布标记为成功。