# Design

## Context

档位名单现为 `orchestrator`、`analysis`、`direction`、`embedding`。每个档位有 `api_base`、`model`、`api_key_env`。本地 `settings.json` 不入库，当前三个对话档位指向同一个对话模型，`embedding` 单独配置。见 `proposal.md` 的 Why。

Paper-Agent 的示例把对话分成 `luna_agent`、`default_agent`、`solar_agent`，向量放在另一份 embedding 配置里。它另外还有服务商、温度、推理强度，以及缺少强弱档时改用 `default_agent`。这些不进入本变更。

## Goals / Non-Goals

**Goals:**

- 对话请求按三个强弱档位各自的 `model` 发出。
- 示例配置、设置接口和连通性测试使用同一组四个名称。

**Non-Goals:**

- 不增加服务商层、温度或推理强度。
- 不为 `multi-agent-research-workflow` 指定每个节点用哪一档。

## Decisions

### 1. 替换三个对话档位名

`PROFILE_NAMES` 改为 `luna_agent`、`default_agent`、`solar_agent`、`embedding`。加载配置时四个名字都必须存在，缺任何一个则配置无效。`embedding` 的连通性测试仍走向量接口，另外三个走对话接口。

备选是允许只配置 `default_agent`，另外两档可选。调用方会分不清自己用的是声明的强档，还是因为缺配置而换成了默认档。

### 2. 未知名字仍然失败

`orchestrator`、`analysis`、`direction` 以及其他不在名单中的名字都返回档位不存在。实现不在缺失时改用 `default_agent`。

备选是照 Paper-Agent 的解析：名单外的名字改用 `default_agent`。这会让强档未配置时仍返回成功，和现有“未知档位不能静默替换”相反。

### 3. 字段保持不变

每个档位继续只保存 `api_base`、`model`、`api_key_env`。对话请求仍只发送模型名和消息。

备选是照 Paper-Agent 增加 `provider`、`temperature`、`reasoning_effort`。当前对话调用没有这些参数，加进配置没有读取方。

### 4. 本地配置沿用现有对话模型

示例配置使用四个档位名，模型名分别写成可区分的占位值，且不含密钥。

若本地 `settings.json` 仍有 `orchestrator`，则 `luna_agent`、`default_agent`、`solar_agent` 都复制 `orchestrator` 的 `api_base`、`model`、`api_key_env`，然后删除三个旧键。`embedding` 原样保留。三个旧档位当前指向同一模型，因此复制后行为与现在一致，用户可以再把弱档和强档改成不同模型。

## Risks / Trade-offs

- [主图设计仍写旧档位名，实现时会调用失败] → 那个变更实现前先选定强弱档位。本变更不提前指定。
- [本地配置未改名时进程无法加载] → 实现任务包含对已存在 `settings.json` 的改名，不把该文件提交入库。

## Migration Plan

先改示例配置和档位名单，再改本地 `settings.json` 的键名。回滚时把四个名字改回 `orchestrator`、`analysis`、`direction`、`embedding`，对话档位恢复为改名前的地址和模型。不改 Milvus 数据。
