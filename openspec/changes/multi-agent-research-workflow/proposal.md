# Proposal

## Why

论文调研需要主 agent 根据中间结果继续调度，例如检索偏了就重检索，研究方向对不上原问题就再派检索。四个 agent 属于同一张图，需要一次变更把回路、状态和分析能力一起定下来。

## What Changes

- 新增星型编排：主 agent 是唯一控制节点，检索、分析、研究方向三个子 agent 只向主 agent 返回。
- 主 agent 每次只发出一条命令：检索、分析、研究方向或结束本轮。同一条命令可以再次发出。
- 检索子 agent 调用 `paper-retrieval-tool` 的检索工具，并用工具的成功结果替换已保存的检索结果。图内不重新实现切块和 arXiv 获取。
- 共享状态保留每个子 agent 的最新成功结果。分析依赖检索结果，研究方向依赖检索结果和分析结果。前置结果不可用时，命令不执行。
- 检索成功写入新结果后，分析和研究方向的旧结果作废。失败不覆盖上一次成功结果。
- 一次用户发言跑一轮图。同一会话的下一轮仍能看见上一轮留下的检索结果、分析结果和研究方向结果。进程按顺序输出命令、子 agent 返回、结果作废和最终回答。

以下内容不在本次范围内：后端进程、模型适配、HTTP 路径、SQLite 会话库、Milvus compose、切块入库实现、前端页面、综述写作、用户直接上传论文。未完成的图不从中断点继续执行；已写入 SQLite 的发言和结果由 `backend-shell` 保留。

假设：

- 回答语言为中文。
- 分析读取命令指定论文的已入库切块，不重新获取论文。
- 研究方向中的判断要能对应到输入中的论文。
- 每轮子 agent 调用上限的具体数值放在设计中。达到上限后主 agent 只能结束本轮。

## Capabilities

### New Capabilities

- `research-orchestration`: 主 agent 的命令回路、检索工具的接入、三份已保存结果、作废规则、失败返回、会话内续轮和有序事件流
- `paper-analysis`: 基于已入库切块解释指定论文
- `research-direction`: 基于检索和分析结果给出研究空白、技术路线和创新点

### Modified Capabilities

无。这三项能力尚未归档到主规格。`paper-retrieval` 改由 `paper-retrieval-tool` 定义。

## Impact

- 把图注册为 `backend-shell` 已有运行接口的处理函数，不新增 HTTP 路径。
- 检索节点依赖 `paper-retrieval-tool`。分析和研究方向使用该工具留下的切块与结果结构。
- `event-stream-frontend` 消费本变更输出的事件，不在这里实现页面。
