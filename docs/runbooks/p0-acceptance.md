# P0 演示与验收手册

## 适用范围

本手册验证 TaxMind Pro 的**虚构/匿名化 P0 专业辅助原型**。它不验证真实客户资料、电子税务局登录、自动申报、缴税或正式税务意见。

## 演示链路

1. 打开 `/cases?preview=1`，展示虚构事项画像与事实版本。
2. 打开 `/policies?preview=1`，展示条款级证据、有效期和全国口径回退提示。
3. 在事项工作台展示确定性风险卡：规则版本、依据条款和缺失事实必须可见。
4. 打开 `/procedures?preview=1`，展示虚构地区化办税事项与官方入口占位。
5. 打开 `/reviews?preview=1` 和审核详情，展示提交、审核动作和版本号。
6. 打开 `/feedback?preview=1`，展示错误反馈不会直接修改正式知识。
7. 打开 `/audit?preview=1`，确认仅有脱敏摘要，未显示审计前后 JSON、IP 或 User-Agent 哈希。

所有页面都必须保留“内部专业辅助”边界提示；预览模式不访问真实客户资料或正式税务资料。

## 自动化门禁

在 `apps/backend` 执行：

```powershell
uv run pytest tests/golden/test_p0_acceptance.py tests/golden/test_p0_performance_smoke.py tests/golden/test_p0_security_boundaries.py tests/unit/test_retrieval_service.py tests/unit/test_feedback_audit_service.py -q --basetemp .pytest-tmp-stage10-golden
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

在仓库根目录执行：

```powershell
pnpm --filter @taxmind/web run typecheck
pnpm --filter @taxmind/web exec eslint . --max-warnings=0
apps/web/node_modules/.bin/vite.cmd build
```

## 依赖降级与环境限制

- Milvus 不可用时，政策检索必须保留 MySQL 精确检索结果并返回 `semantic_retrieval_unavailable`，不得虚构语义召回结果。
- 缺少 `business_date` 或 `region_code` 时，查询必须进入 `need_info`，不得执行确定性风险结论。
- 没有地方证据时，办税/政策结果必须标明全国口径回退，不能伪装成本地办理口径。
- 若 Docker 的 MinIO 端口 `9000` 被宿主机占用或代理影响 Milvus gRPC，本次验收只记录该依赖未就绪；不得把未运行的 Milvus 结果记为通过。

## 性能烟雾检查

- 金标准中的一秒门禁仅覆盖进程内的范围闸门与确定性路由；它不是政策检索、向量召回或模型生成的端到端性能承诺。
- 设计目标中的“政策首屏 95% 3 秒、条款定位 95% 2 秒、复杂分析阶段反馈 5 秒/首版 60 秒”需要在 Milvus、Neo4j、模型服务均已就绪的独立压测环境测量后才能报告为实测结果。

## 通过判定

- 金标准必须全部通过：范围闸门、规则确定性、规则依据、审计字段脱敏，以及审计读取和反馈治理的权限隔离。
- 前端预览页在 1440px 桌面宽度可正常展示，控制台无阻塞错误。
- 代码静态检查、类型检查和生产构建通过。
- 任何外部依赖阻塞必须在交付记录中逐项列出；它不等同于功能已通过端到端验证。
