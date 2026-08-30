# TaxMind Pro Backend

当前后端仅实现工程 Bootstrap：配置、日志、应用工厂、请求上下文、统一错误和健康检查。
它不包含数据库模型、税务规则、检索、工作流或模型调用。

```powershell
uv sync --all-groups
uv run uvicorn taxmind.entrypoints.api.main:create_app --factory --reload --port 8000
uv run pytest tests -v
```