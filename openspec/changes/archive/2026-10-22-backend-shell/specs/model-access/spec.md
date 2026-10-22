# Spec Delta

## Purpose

按已配置的模型档位，通过 OpenAI 兼容接口完成对话和文本向量化，供检索工具与 agent 图使用。

## ADDED Requirements

### Requirement: 按档位返回对话文本
系统 SHALL 使用调用方指定的已配置档位发起对话，并把模型返回的文本交给调用方。

#### Scenario: 编排档位返回文本
- **WHEN** 编排档位已配置，且对话接口返回一段文本
- **THEN** 调用方得到这段文本

### Requirement: 按档位返回向量
系统 SHALL 使用 embedding 档位把文本转换为数值向量，并把该向量交给调用方。

#### Scenario: embedding 档位返回向量
- **WHEN** embedding 档位已配置，且接口返回一个数值向量
- **THEN** 调用方得到这个向量

### Requirement: 未知档位不能静默替换
调用方指定的档位不存在时，系统 MUST 使本次调用失败，并 MUST NOT 改用另一个档位继续完成调用。

#### Scenario: 未配置档位导致失败
- **WHEN** 调用方使用示例配置中不存在的档位
- **THEN** 调用失败，并说明该档位不存在
