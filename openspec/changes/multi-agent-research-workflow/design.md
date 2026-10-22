# Design

## Context

`backend-shell` 提供进程、四个模型档位和健康检查。`paper-retrieval-tool` 提供检索工具和按论文读取切块的存储接口。见 `proposal.md` 的 Why。本变更把四个 agent 放进同一张图，并通过事件流把调度过程交出去。

## Goals / Non-Goals

**Goals:**

- 主节点可以反复进入，子节点只返回主节点。
- 前置检查、失败保留和下游作废由代码执行。
- 检索节点只转调检索工具。
- 同一会话能保留三份成功结果，并以固定事件名输出过程。这些结果随会话写入 SQLite。

**Non-Goals:**

- 不实现切块、Milvus 写入、arXiv 获取和 compose。
- 不实现页面。页面由 `event-stream-frontend` 消费这里的事件。
- 不从中断点继续执行未完成的图。

## Decisions

### 1. 手写 StateGraph

节点为 `master`、`retrieval`、`analysis`、`direction`。`master` 条件进入其中一个子节点或结束。三个子节点只连回 `master`。

备选是预置 supervisor，把子 agent 当主节点内部的工具。前置检查和作废会留在提示词里，状态规则无法单独测试。

### 2. 每次一条结构化命令

`master` 使用 `orchestrator` 档位，读取用户问题、三份成功结果的摘要、最近一次失败或拒绝，以及本轮已调用次数。输出 `command` 和 `payload`。

- `retrieve.payload` 包含 `query`，原样交给检索工具。
- `analyze.payload` 包含 `paper_ids`。分析用 `analysis` 档位，并按 `paper_id` 读取检索工具存储的切块。
- `direction.payload` 可为空，使用 `direction` 档位。
- `finish.payload` 包含中文回答。

分析对单篇切块按顺序截断到固定字符预算，并在结果中标明已截断。只有 `abstract` 切块时标明缺少正文。

### 3. 状态与上限

状态保留原始问题、三份成功结果、最近一次失败或拒绝、本轮调用次数和事件列表。检索工具成功才替换已保存的检索结果，并清掉已保存的分析结果和研究方向结果。失败不替换已保存的成功结果。

一轮最多执行 8 次子 agent。拒绝不计次，失败计次。达到上限后只能 `finish`，回答说明达到上限。8 次覆盖两次检索、分析、研究方向、再检索、再分析、再研究方向。

三份结果保存在 `backend-shell` 的 SQLite 会话记录里。成功结果一产生就写入。一个会话看不到另一个会话已保存的结果。进程重启后，下一轮从图读取已经写入的结果，不从中断点继续执行上一轮未完成的命令。

### 4. 事件名

按实际顺序追加：`command.issued`、`command.rejected`、`worker.completed`、`worker.failed`、`state.invalidated`、`run.completed`。这些事件写入 `backend-shell` 已有的运行事件流。前端变更只依赖这些名称和顺序。

研究方向返回后，用代码剔除不在当前输入中的论文标识。某一项因此没有依据时，保留该项并标明依据不足。

## Risks / Trade-offs

- [8 次上限提前结束复杂问题] → 回答说明达到上限。数字只在本变更的配置中。
- [检索工具的结果过大，主 agent 读到全文] → 主 agent 只接收论文标识、题名、数量和来源摘要。切块正文留在分析和存储接口中。
- [模型写出输入之外的论文标识] → 研究方向在返回前用代码剔除。

## Migration Plan

依赖 `backend-shell` 已能启动，且 `paper-retrieval-tool` 的检索工具和按论文读切块接口可用。本变更追加 `max_worker_calls_per_turn=8`。回滚时去掉会话和图路由，不删除向量集合。

## Open Questions

无。事件名、上限和档位已经足够支撑后续前端变更。
