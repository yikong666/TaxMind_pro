# 本地开发手册

## 前置环境

- Python 3.12（由 uv 自动管理，不使用系统 Python 3.14 运行项目）。
- Node.js 24。
- pnpm 11.x；仓库声明的版本为 11.14.0。

## Windows

```powershell
./scripts/bootstrap.ps1
./scripts/export-openapi.ps1
./scripts/generate-web-client.ps1

Set-Location apps/backend
uv run uvicorn taxmind.entrypoints.api.main:create_app --factory --reload --port 8000
```

另开终端：

```powershell
pnpm --filter @taxmind/web dev
```

## 检查

```powershell
Set-Location apps/backend
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src tests
uv run pytest tests -v

Set-Location ../..
pnpm lint:web
pnpm typecheck:web
pnpm test:web
pnpm build:web
```

运行日志同时输出到控制台和仓库 `var/log/taxmind/`。该目录被 Git 忽略。
当前基础设施尚未接入，因此 `/health/ready` 返回 `not_ready` 是预期状态，不表示 liveness 失败。