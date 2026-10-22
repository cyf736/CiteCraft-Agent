# Design

## Context

`multi-agent-research-workflow` 用 SSE 发送 `command.issued`、`command.rejected`、`worker.completed`、`worker.failed`、`state.invalidated` 和 `run.completed`。见 `proposal.md` 的 Why。本变更只增加消费这些事件的页面。

## Goals / Non-Goals

**Goals:**

- 一个页面可以读回已保存的会话，提交发言，并按顺序渲染新事件。
- 开发时代理到 `backend-shell` 的后端地址。

**Non-Goals:**

- 不移植 Paper-Agent 的整套工作台。
- 不在页面中实现检索、分析或调度。

## Decisions

### 1. React 与 Vite

使用一个 React 页面。开发服务器把 `/api` 代理到后端。页面先读取 `GET /api/sessions` 和 `GET /api/sessions/{session_key}`，显示已保存的发言、事件和最终回答。新发言发往 `POST /api/sessions/{session_key}/runs`，再订阅响应中的 `stream_url`。

项目约束指定 React。页面只做事件列表和会话选择，不搬移 Paper-Agent 的写作工作台。

### 2. 渲染顺序等于接收顺序

页面把事件追加到列表，不按类型重新分组。`state.invalidated` 因此自然出现在后收到的 `command.issued` 之前。`run.completed` 的回答单独显示为最终回答。

测试使用固定 SSE 夹具，不启动 agent 图。

## Risks / Trade-offs

- [后端事件字段以后增加] → 页面忽略未知字段，已知的六类事件仍按顺序显示。
- [代理端口与后端不一致] → 代理目标集中在一处配置，并在 README 写明默认端口。

## Migration Plan

在后端会话接口可用后启动前端开发服务器。回滚时删除前端目录，不影响图和向量库。

## Open Questions

无。事件名已由 agent 图变更固定。
