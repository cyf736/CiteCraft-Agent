# http-api Specification

## Purpose

用 FastAPI 提供设置、会话和运行事件流接口。会话、发言、最终回答和三份研究结果写入 SQLite，进程重启后仍可读取。路由只解析请求和返回响应，研究流程由可替换的运行处理函数执行。

## Requirements

### Requirement: 设置接口读写四个档位
系统 SHALL 通过 `GET /api/settings` 返回编排、分析、研究方向和 embedding 四个档位的配置，且响应 MUST NOT 包含密钥。系统 SHALL 通过 `PUT /api/settings/profiles/{name}` 更新其中一个档位。`name` 不是这四个名称时 MUST 返回 404。

#### Scenario: 读取设置时不返回密钥
- **WHEN** 客户端请求 `GET /api/settings`
- **THEN** 响应包含四个档位，且没有密钥

#### Scenario: 更新已知档位
- **WHEN** 客户端向 `PUT /api/settings/profiles/analysis` 提交该档位的新地址
- **THEN** 随后的 `GET /api/settings` 返回这个新地址

#### Scenario: 重启后档位地址仍在
- **WHEN** 客户端更新 analysis 档位地址后进程重新启动
- **THEN** `GET /api/settings` 返回该地址，且响应没有密钥

#### Scenario: 未知档位
- **WHEN** 客户端更新一个不存在的档位名
- **THEN** 响应状态为 404，正文为 `error.message` 和 `error.status`

### Requirement: 可以测试档位连通性
系统 SHALL 通过 `POST /api/settings/model-connectivity` 按档位名测试模型连通性，并返回成功或失败。

#### Scenario: 已配置档位测试成功
- **WHEN** 客户端为已配置的 embedding 档位请求连通性测试，且模型接口可用
- **THEN** 响应表明该档位连通成功

### Requirement: 会话可以创建、列出、读取和删除
系统 SHALL 提供 `POST /api/sessions`、`GET /api/sessions`、`GET /api/sessions/{session_key}` 和 `DELETE /api/sessions/{session_key}`。创建成功时 MUST 返回 201 和 `session_key`。读取或删除不存在的会话 MUST 返回 404。

#### Scenario: 新建会话出现在列表中
- **WHEN** 客户端创建一个会话后再请求会话列表
- **THEN** 列表包含该 `session_key`

#### Scenario: 删除后不能再读取
- **WHEN** 客户端删除一个已存在的会话后再读取它
- **THEN** 读取响应状态为 404

### Requirement: 会话内容写入 SQLite
系统 SHALL 把会话、用户发言、最终回答、运行事件、检索结果、分析结果和研究方向结果写入 SQLite。读取会话时 MUST 返回已保存的发言、最终回答和三份结果。进程重启后这些内容 MUST 仍然可读。删除会话时 MUST 删除对应记录。

#### Scenario: 重启后仍能读到发言和结果
- **WHEN** 会话已有用户发言、最终回答和检索结果，并且进程重新启动
- **THEN** 读取该会话仍返回这些内容

#### Scenario: 删除后重启也不再出现
- **WHEN** 客户端删除会话后进程重新启动
- **THEN** 会话列表不再包含该会话

### Requirement: 发言通过运行接口进入事件流
系统 SHALL 通过 `POST /api/sessions/{session_key}/runs` 接受用户发言，返回 202，以及 `run_id` 和 `stream_url`。`stream_url` MUST 指向 `GET /api/sessions/{session_key}/runs/{run_id}/stream`。该 GET 接口 MUST 以 `text/event-stream` 按发生顺序输出事件。

#### Scenario: 创建运行后能订阅事件
- **WHEN** 客户端向一个已存在的会话提交发言
- **THEN** 响应状态为 202，并包含 `run_id` 和对应的 `stream_url`

#### Scenario: 不存在的会话不能创建运行
- **WHEN** 客户端向一个不存在的 `session_key` 提交发言
- **THEN** 响应状态为 404，正文包含 `error.message` 和 `error.status`

### Requirement: 同一会话不能并行运行
会话已有未结束的运行时，新的发言 MUST 返回 409，且 MUST NOT 启动第二轮研究流程。

#### Scenario: 第二次提交被拒绝
- **WHEN** 一个运行尚未结束，客户端再次向同一会话提交发言
- **THEN** 响应状态为 409，已保存的结果不被第二轮修改

### Requirement: 重启后解除运行锁
进程启动时，系统 SHALL 把仍标记为运行中的会话改为已中断，清除运行锁，并保留已写入的发言和结果。系统 MUST NOT 从中断点继续执行研究流程。

#### Scenario: 中断的会话可以再次发言
- **WHEN** 会话在运行过程中进程退出，然后进程重新启动
- **THEN** 读取会话仍能看到中断前已保存的发言和结果，并且可以再次提交发言

### Requirement: 等待事件时发送心跳
事件流在等待下一条研究事件时 SHALL 发送 SSE 注释心跳。心跳 MUST NOT 被当作检索结果、分析结果、研究方向结果或最终回答。

#### Scenario: 心跳不改变研究结果
- **WHEN** 运行处理函数暂时没有新事件
- **THEN** 事件流出现注释心跳，已保存的三份结果保持不变

### Requirement: 运行可以停止
系统 SHALL 通过 `POST /api/sessions/{session_key}/runs/{run_id}/cancel` 接受停止请求。运行仍在进行时 MUST 返回 202，且事件流随后结束。运行不存在时 MUST 返回 404。

#### Scenario: 停止后事件流结束
- **WHEN** 客户端对一个正在进行的运行请求停止
- **THEN** 停止请求返回 202，对应的事件流随后结束

### Requirement: 没有研究流程时不编造结论
尚未注册研究流程处理函数时，系统 MUST 让该次运行以失败事件结束，且 MUST NOT 生成检索结果、分析结果、研究方向结果或研究结论。

#### Scenario: 未接入图时运行失败
- **WHEN** 应用没有注册研究流程处理函数，客户端提交发言并订阅事件流
- **THEN** 事件流以失败结束，且没有研究结论
