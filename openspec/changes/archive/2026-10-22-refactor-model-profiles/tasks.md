# Tasks

## 1. 档位名单与示例配置

- [x] 1.1 把示例配置和 `PROFILE_NAMES` 改为 `luna_agent`、`default_agent`、`solar_agent`、`embedding`，并更新 README 中的档位名。验证：测试确认示例配置的档位名是这四个；README 写明这四个名字。

## 2. 对话调用

- [x] 2.1 对话按档位使用各自的模型；`orchestrator` 等未知名字失败，不改用 `default_agent`。验证：伪造 HTTP 的测试确认 `default_agent` 返回文本；`luna_agent` 与 `solar_agent` 配置不同模型名时，两次请求的模型名分别等于这两个配置；调用 `orchestrator` 失败并说明档位不存在，且没有发出 `default_agent` 的请求。

## 3. 设置接口

- [x] 3.1 设置读写和连通性测试使用新的四个档位名。验证：`GET /api/settings` 返回这四个档位且没有密钥；`PUT /api/settings/profiles/default_agent` 更新地址后重新加载仍能读到，响应没有密钥；`PUT /api/settings/profiles/orchestrator` 返回 404；已配置的 `embedding` 连通性测试在模型接口可用时成功。

## 4. 本地配置

- [x] 4.1 若 `backend/config/settings.json` 仍含 `orchestrator`，则 `luna_agent`、`default_agent`、`solar_agent` 都复制该档位的 `api_base`、`model`、`api_key_env`，删除 `orchestrator`、`analysis`、`direction`，并保留 `embedding`。验证：改写后的文件含四个新档位、不含三个旧档位；三个对话档位的模型与改写前的 `orchestrator` 相同；`embedding` 的模型不变。不把该文件加入 git。

## Workflow follow-up

- 实现完成并经过复查后，再归档本次变更。
- 归档后确认主规格中的 `model-access` 和 `http-api` 已改为强弱档位名。
