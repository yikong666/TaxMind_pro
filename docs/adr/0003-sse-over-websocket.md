# ADR 0003：MVP 使用 SSE

- 状态：Accepted
- 日期：2026-08-30

REST JSON 承载命令和查询，SSE 承载服务端单向运行状态与答案增量。客户端使用带 Bearer Token 的
`fetch` 流，访问令牌不放入 URL。MVP 不引入 WebSocket。