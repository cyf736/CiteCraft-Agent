# Proposal

## Why

agent 图和检索工具都需要一个已经能启动的后端来读取配置并调用模型。CiteCraft-Agent 目前没有这个进程，也没有本地向量库的运行环境。

## What Changes

- 建立可启动的后端进程，并提供健康检查。
- 提供示例配置，包含编排、分析、研究方向和 embedding 四个模型档位，以及 Milvus 地址。应用配置不写 MinIO 地址或凭据。
- 用 compose 启动 Milvus，并由 Milvus 依赖 etcd 和 MinIO。MinIO 只服务 Milvus。
- 提供 OpenAI 兼容的对话和 embedding 调用。未知档位时失败，不静默替换成其他档位。
- 按 Paper-Agent 的薄路由方式提供 FastAPI 接口：设置、会话、创建运行、停止运行和 SSE 事件流。路由只处理请求和响应，研究流程由可替换的处理函数执行。
- 会话、发言、最终回答、运行事件和三份研究结果写入 SQLite。档位修改写入本地配置。二者在进程重启后仍可读取。
- 同一会话已有未结束运行时，新的发言返回 409。进程启动时把上次中断的运行标记为中断并解除锁定，不从中断点继续执行图。
- 尚未注册研究流程时，运行以失败事件结束，不生成研究结论。

本次不实现 agent 图、论文切块、arXiv 获取和前端页面。不提供写作产物下载，也不保留同步等待整次运行结束的旧消息接口。检索阈值、每轮调用上限等业务参数留给后续变更。

## Capabilities

### New Capabilities

- `backend-runtime`: 后端进程的健康检查、模型与 Milvus 配置，以及只供 Milvus 使用的本地依赖
- `model-access`: 按档位进行 OpenAI 兼容的对话和文本向量化
- `http-api`: 设置、会话、运行和 SSE 事件流的 FastAPI 接口

### Modified Capabilities

无。主规格目录中还没有已归档能力。

## Impact

- 后端项目放在 `backend/`，入口是 FastAPI。仓库根目录提供 Milvus compose 和 README。`front/` 只有空白页面入口，页面行为不属于本次变更。
- `paper-retrieval-tool` 依赖这里的配置和模型适配。`multi-agent-research-workflow` 把图注册为运行处理函数，不另建一套 HTTP 路径。
- 进程保存 Milvus 地址，并在调用时连接已配置的模型服务。这一阶段不安装 Milvus 客户端，也不连接 etcd 或 MinIO。
