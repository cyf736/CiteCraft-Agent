# Design

## Context

CiteCraft-Agent 没有业务代码。arxiv-agent 用 compose 启动 Milvus，并由 Milvus 连接 etcd 和 MinIO。Paper-Agent 用可配置的 OpenAI 兼容客户端调用模型。见 `proposal.md` 的 Why。本变更建立进程、配置、模型调用，以及设置、会话和运行事件流的 HTTP 接口。

## Goals / Non-Goals

**Goals:**

- 后端进程可以启动，健康检查可用。
- 示例配置表达四个模型档位和 Milvus 地址。
- 对话与 embedding 共用一套 OpenAI 兼容适配。
- 设置、会话、运行和 SSE 的路径在这里固定下来。

**Non-Goals:**

- 不实现切块、arXiv、agent 图和页面。
- 不提供产物文件下载，也不提供会一直等待到运行结束的同步消息接口。
- 不在应用配置中填写 MinIO 地址或凭据。

## Decisions

### 1. FastAPI 作为进程入口

使用 uv 和 Python 3.12。Python 项目放在 `backend/`，`create_app()` 位于 `src.api.app`，读取配置并挂载健康检查。后续变更往同一个应用上增加路由。

备选是先写脚本、后补 HTTP。检索工具和页面都要连接一个稳定入口，先把进程定下来。

### 2. 一份示例配置

配置包含 `orchestrator`、`analysis`、`direction`、`embedding` 四个档位，以及 Milvus 的 host 和 port。密钥只通过环境变量或本地未提交文件提供，示例文件不含密钥。

检索阈值和调用上限不在本变更的配置契约里。后续变更可以追加自己的键。

### 3. compose 只部署向量库

compose 包含 etcd、MinIO 和 Milvus。只有 Milvus 服务接收 MinIO 地址。应用代码不创建 MinIO 客户端。本变更只把 Milvus 地址放进应用配置，不安装 Milvus 客户端，也不在进程里建立连接。检索变更再使用这个地址。

这沿用 arxiv-agent 的部署关系。备选是把 MinIO 做成应用自己的论文桶。当前没有论文文件库。

### 4. 模型适配不绑定单一供应商

从 Paper-Agent 的 OpenAI 兼容调用方式收窄出对话和 embedding 两个方法。档位名必须存在于配置中，缺失时返回错误。

备选是直接使用 arxiv-agent 的 DashScope 客户端。那会把后续工具和图绑到一个供应商。

### 5. HTTP 接口沿用 Paper-Agent 的分层

FastAPI 路由分成设置和会话两组，路由函数只解析请求、调用服务并转换错误。统一错误正文为 `{"error": {"message": "...", "status": <http_status>}}`。

- `GET /health`
- `GET /api/settings`
- `PUT /api/settings/profiles/{name}`，`name` 为 `orchestrator`、`analysis`、`direction` 或 `embedding`
- `POST /api/settings/model-connectivity`
- `GET /api/sessions`
- `POST /api/sessions`
- `GET /api/sessions/{session_key}`
- `DELETE /api/sessions/{session_key}`
- `POST /api/sessions/{session_key}/runs`，返回 202、`run_id` 和 `stream_url`
- `POST /api/sessions/{session_key}/runs/{run_id}/cancel`
- `GET /api/sessions/{session_key}/runs/{run_id}/stream`，响应类型为 `text/event-stream`

会话数据库使用 SQLite，表包括会话、发言、运行事件和三份研究结果。用户发言在运行被接受时写入；最终回答、事件和每份成功结果在产生时写入。`GET /api/sessions/{session_key}` 返回这些内容。删除会话时删除对应的行。

同一会话存在未结束运行时，新的运行返回 409。进程启动时，仍标记为运行中的会话改为已中断，清除运行锁，并追加一条中断事件。已写入的发言和结果保留。启动过程不继续执行图。

等待下一条事件时，SSE 发送注释心跳。心跳不是研究事件。创建运行时调用已注册的处理函数；没有处理函数时，事件流以失败事件结束。`multi-agent-research-workflow` 注册真正的图处理函数。

档位修改写入本地配置文件。示例配置仍不含密钥，`GET /api/settings` 也不返回密钥。

Paper-Agent 里的产物下载、同步等待消息接口和静态页面挂载不进入本接口。前两项属于写作产物和旧兼容路径，静态页面属于前端变更。

## Risks / Trade-offs

- [健康检查在 Milvus 未启动时仍返回成功] → 健康检查只表示进程存活。Milvus 连通性由检索工具在真正查询时报告失败。
- [示例配置被写入真实密钥] → 示例文件使用占位符，README 说明密钥放在本地文件或环境变量中。

## Migration Plan

空项目上的首次骨架，没有旧数据。

1. 在 `backend/` 执行 `uv sync`，安装 FastAPI、httpx、uvicorn 和测试依赖。不在这一步安装 Milvus 客户端。
2. 复制示例配置并填入本地密钥。
3. 需要向量库时启动 compose。
4. 回滚时停止进程和 compose。

## Open Questions

- 具体模型供应商、接口地址和密钥在本地配置中填写，不改变四个档位的名称。
