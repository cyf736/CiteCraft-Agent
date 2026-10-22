# CiteCraft

本地研究助手。后端在 `backend/`，页面在 `front/`。这一阶段后端提供进程、模型配置、会话和运行事件流。页面目前只有一个空白入口。

## 准备配置

复制示例配置。示例里没有密钥，也没有 MinIO 地址。

```powershell
Copy-Item backend\config\settings.example.json backend\config\settings.json
```

四个模型配置是 `luna_agent`、`default_agent`、`solar_agent`、`embedding`。前三个是对话档位，按基础、默认、最高能力区分。`embedding` 只做向量。每个配置有 `api_base`、`model`、`api_key_env`。密钥放在对应的环境变量里。

Milvus 地址由 `milvus.host` 和 `milvus.port` 指定，默认是 `127.0.0.1` 和 `19530`。

## 启动 Milvus

compose 会同时启动 etcd、MinIO 和 Milvus。应用只连接 Milvus。

```powershell
docker compose up -d
```

## 启动后端

```powershell
cd backend
uv sync
uv run citecraft
```

健康检查：<http://127.0.0.1:8000/health>

设置：`GET /api/settings`

会话：`POST /api/sessions`

## 启动页面

```powershell
cd front
npm install
npm run dev
```

页面地址：<http://127.0.0.1:5173>
