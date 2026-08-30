# Changelog

## 2026-08-30

### 工程基座（未发布）

- 初始化 TaxMind Pro Monorepo 工具链和文档目录。
- 增加 FastAPI 应用工厂、运行日志、统一错误、请求 ID 和健康检查基线。
- 增加 React 工作台最小应用壳、健康状态和内部专业辅助提示。
- 增加 OpenAPI 导出、前端类型生成、单元测试、契约测试和 CI 基线。

影响模块：仓库基础设施、Backend Bootstrap、Web Bootstrap、Contracts。

迁移与回滚：不包含数据库迁移或业务数据；删除本批新增文件即可回滚，现有 `AGENTS.md` 未被覆盖。

验证结果：以本轮实际检查结果为准，完成后补充到任务交付记录。