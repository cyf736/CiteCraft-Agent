# Proposal

## Why

对话档位现在按编排、分析、研究方向命名。三个职责可以共用一个模型，也可以各自需要更弱或更强的模型，按职责命名无法表达这种选择。

## What Changes

- **BREAKING** 三个对话档位改为按能力命名：`luna_agent` 是基础能力，适合简单任务；`default_agent` 是中等能力，作为默认对话档位；`solar_agent` 是最高能力，适合最难任务。
- `embedding` 仍是独立的向量档位，不参与强弱划分。
- 四个档位都仍须配置。调用 `luna_agent`、`default_agent` 或 `solar_agent` 时使用该档位自己的模型。未配置的名字，包括原来的 `orchestrator`、`analysis`、`direction`，调用失败，不改用另一个档位。
- 设置接口改为读写这四个名称。每个档位仍只有接口地址、模型名和密钥环境变量。

本次不引入按服务商拆开的连接配置，也不增加温度、推理强度等生成参数。不把缺少 `luna_agent` 或 `solar_agent` 时自动改用 `default_agent`。三个对话档位都必须存在，调用哪一档就使用哪一档的模型。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `model-access`: 对话按三个强弱档位各自的模型调用；未知档位仍失败
- `http-api`: 设置接口读写 `luna_agent`、`default_agent`、`solar_agent` 和 `embedding`

## Impact

- 修改 `backend/config/settings.example.json`、档位名单、模型调用测试、设置接口测试和 README 中的档位名。
- 本地 `backend/config/settings.json` 不入库。实现时若该文件仍使用旧档位名，把三个对话档位改成新名称，并沿用其中已有的对话地址和模型；`embedding` 保持不变。
- `paper-retrieval-tool` 继续使用 `embedding`。
- `agent-framework` 只保存档位名，不在本变更中改写。
- `multi-agent-research-workflow` 的设计仍写着旧档位名。本次不决定主节点、分析和研究方向各用哪一档；实现那个变更时再选。
