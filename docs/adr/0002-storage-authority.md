# ADR 0002：MySQL 为结构化事实源

- 状态：Accepted
- 日期：2026-08-30

MySQL 保存事实、版本、审核、审计、关系台账和 Outbox。Milvus 与 Neo4j 是已发布知识的可重建投影，
Redis 只保存短期状态。API 不在同一请求事务内跨存储双写。