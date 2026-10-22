# Proposal

## Why

agent 图会按顺序发出命令、子 agent 返回、结果作废和最终回答。需要一个页面把这些事件原样显示出来，避免在实现图的同一次变更里同时做界面。

## What Changes

- 增加一个页面，用来提交当前会话的发言。
- 打开页面时读取已有会话，并显示已保存的发言、运行事件和最终回答。
- 页面按收到的顺序显示 `multi-agent-research-workflow` 定义的新事件。
- 结果作废显示在其后的下一条命令之前。本轮结束时显示最终回答。
- 页面不自行生成检索、分析或研究方向结论。

本次不实现后端进程、检索工具和 agent 图。页面只消费已经约定的事件流。

## Capabilities

### New Capabilities

- `event-stream-ui`: 提交发言，并按事件流顺序显示调度过程和最终回答

### Modified Capabilities

无。主规格目录中还没有已归档能力。

## Impact

- 新增一个 React 页面和它的开发代理。
- 依赖 `backend-shell` 的会话和运行接口，以及 `multi-agent-research-workflow` 的事件名。
- 不改变图的状态规则，也不调用检索工具。
