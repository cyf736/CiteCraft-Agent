# Spec Delta

## MODIFIED Requirements

### Requirement: 设置接口读写四个档位
系统 SHALL 通过 `GET /api/settings` 返回 `luna_agent`、`default_agent`、`solar_agent` 和 `embedding` 四个档位的配置，且响应 MUST NOT 包含密钥。系统 SHALL 通过 `PUT /api/settings/profiles/{name}` 更新其中一个档位。`name` 不是这四个名称时 MUST 返回 404。

#### Scenario: 读取设置时不返回密钥
- **WHEN** 客户端请求 `GET /api/settings`
- **THEN** 响应包含这四个档位，且没有密钥

#### Scenario: 更新已知档位
- **WHEN** 客户端向 `PUT /api/settings/profiles/default_agent` 提交该档位的新地址
- **THEN** 随后的 `GET /api/settings` 返回这个新地址

#### Scenario: 重启后档位地址仍在
- **WHEN** 客户端更新 `default_agent` 档位地址后进程重新启动
- **THEN** `GET /api/settings` 返回该地址，且响应没有密钥

#### Scenario: 未知档位
- **WHEN** 客户端更新 `orchestrator`
- **THEN** 响应状态为 404，正文为 `error.message` 和 `error.status`
