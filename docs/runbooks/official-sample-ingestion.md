# 官方小样本资料下载与导入

## 范围与安全边界

- 仅使用 `data/manifests/official-sample-2026-09-02.json` 中经用户确认的 HTTPS 官方公开 URL。
- 下载器每个来源只请求一次、间隔一秒；禁止登录、验证码、反爬绕过、代理池或替换为未确认 URL。
- 原件写入被 Git 忽略的 `.data/official-samples/<date>/`；`receipt.json` 记录下载时间、来源 URL、MIME、大小、SHA-256 和安全失败摘要。
- 下载成功不代表资料已经审核、发布、激活或可用于工作台回答。

## 执行

```powershell
$env:PYTHONPATH = 'apps/backend/src'
apps/backend/.venv/Scripts/python.exe scripts/download_official_sample.py `
  --manifest data/manifests/official-sample-2026-09-02.json `
  --output-dir .data/official-samples/2026-09-02
```

只有 `receipt.json` 中 `status=downloaded` 的项目可进入下一步。失败项目不得以替代链接、缓存或手工内容代替；需要新增来源时，先向用户展示精确 URL 并取得新确认。

## 已验证下载记录（2026-09-02）

| 项目 | 状态 | 文件 | SHA-256 | 本地解析预检 |
| --- | --- | --- | --- | --- |
| `national-2023-12` | downloaded/imported as draft | HTML，42,764 bytes | `5e2ab42fade216e8ff30720b8a29be374354afb2420d569e1da97ebaf754a610` | 131 chunks |
| `national-policy-guide-2` | downloaded/imported as draft | PDF，15,558,275 bytes | `d4cb56e6c504195fb645bdb3b4ad078e87b080055e9cc91be0fef6cf471c7898` | 1 chunk |
| `guangdong-2023-qa` | downloaded/imported as draft | PDF，259,554 bytes | `eba122c909046f22443092d6b02575892f01023fa8e616a172c944e771931b4a` | 1 chunk |
| `shenzhen-2023-individual-businesses` | failed | — | — | TLS `BAD_ECPOINT`；未导入、未替换来源 |

三个成功文件已在隔离 MySQL/MinIO 验收环境以 `knowledge_admin` 身份登记来源、上传并保存为草稿，作业均为 `succeeded`。PDF 文件当前各只产生一个大块；在进入候选审核前，应先检查分块质量，必要时实施受控的 PDF 分块改进并补充测试，不能据此自动发布。

## 受控导入顺序

1. 在目标机构登记与来源 URL 同域的白名单来源，收集方式为 `file_import`。
2. 仅将成功下载的原件经 `POST /api/v1/knowledge/uploads` 发送；提交 manifest 中的标题、发布机关、地区、文号、日期和规范 URL。
3. 确认 `ingestion_job`、原件对象键、文档版本和分块数已持久化，且文档为草稿/待审核。
4. 经人工审核生成知识候选；候选通过后创建发布批次、校验、物化快照并按既有激活门禁执行。
5. 使用虚构事项验证地域、业务日期、知识快照和引用约束；没有已发布证据时工作台必须保持追问、失败或排队状态，不能生成答案。

## 回滚与保留

- 删除本地 `.data` 原件只影响本机下载缓存，不删除任何 MySQL 审计、文档版本或对象存储原件。
- 已导入资料如需撤回，走文档/候选/快照的受控状态流转；不得直接删除审计记录或覆盖已发布版本。
