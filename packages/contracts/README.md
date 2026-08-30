# TaxMind Pro Contracts

- `openapi/taxmind-v1.openapi.json` 由 FastAPI 应用导出，是同步 HTTP 契约的事实源。
- `json-schema/` 保存 SSE、EvidenceBundle、风险规则和生成输出等独立版本化契约。
- `apps/web/src/api/generated/` 由 OpenAPI 生成，不手工编辑，也不提交 Git。

生成命令：

```powershell
./scripts/export-openapi.ps1
./scripts/generate-web-client.ps1
```