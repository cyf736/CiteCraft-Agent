# Tasks

## 1. 运行骨架

- [x] 1.1 用 uv 建立 Python 3.12 项目，安装 FastAPI 和测试依赖，并加入不含密钥的示例配置。验证：`uv sync` 成功；示例配置含 `orchestrator`、`analysis`、`direction`、`embedding` 和 Milvus 地址，且没有 MinIO 地址、凭据或真实密钥。
- [x] 1.2 添加 etcd、MinIO 和 Milvus 的 compose，并在 README 写明启动 compose、复制配置和启动进程的步骤。验证：compose 中只有 Milvus 服务配置 MinIO 地址，README 里的配置键与示例配置一致。
- [x] 1.3 实现应用入口和健康检查。验证：使用示例配置启动测试客户端时，健康检查返回成功。

## 2. 模型适配

- [x] 2.1 实现 OpenAI 兼容的对话和 embedding 调用，并按档位读取配置。验证：伪造 HTTP 响应的测试能拿到对话文本和数值向量。
- [x] 2.2 对不存在的档位返回失败。验证：测试使用示例配置中没有的档位时调用失败，且不会发出另一个档位的请求。

## 3. HTTP 接口

- [x] 3.1 实现设置路由：`GET /api/settings`、`PUT /api/settings/profiles/{name}` 和 `POST /api/settings/model-connectivity`。验证：测试确认响应含四个档位且不含密钥，未知档位返回 404 和 `error.message`，连通性测试能区分成功和失败；更新地址并重新打开配置后，新进程仍返回该地址且没有密钥。
- [x] 3.2 用 SQLite 实现会话的创建、列表、读取和删除，并保存发言、最终回答、运行事件和三份研究结果。验证：关闭并重新打开数据库后仍能读到这些内容；删除后再打开不再出现；另一个会话读不到这份会话。
- [x] 3.3 实现 `POST /runs`、`POST /cancel` 和 SSE `GET /stream`。验证：测试用伪造处理函数确认 202 响应含 `run_id` 与 `stream_url`，事件按处理函数给出的顺序到达，等待期间有注释心跳；同一会话已有未结束运行时再次提交返回 409；不存在的会话返回 404；未注册处理函数时事件流以失败结束且没有研究结论；停止请求返回 202 后流结束。
- [x] 3.4 进程启动时把仍标记为运行中的会话改为已中断，清除运行锁，并保留已有发言和结果。验证：重启后的测试可以再次提交发言，且读到的发言与重启前一致，测试没有继续执行研究流程。

## Workflow follow-up

- 实现完成并经过复查后，再归档本次变更。
- 归档后确认主规格包含 `backend-runtime`、`model-access` 和 `http-api`。
