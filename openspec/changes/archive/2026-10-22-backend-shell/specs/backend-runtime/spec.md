# Spec Delta

## Purpose

提供可启动的后端进程和健康检查，读取模型档位与 Milvus 地址，并用 compose 准备 Milvus 及其依赖的 etcd 和 MinIO。应用配置不包含 MinIO 凭据。

## ADDED Requirements

### Requirement: 进程提供健康检查
系统 SHALL 在示例配置完整时启动进程。健康检查成功时 MUST 表示进程正在接收请求。

#### Scenario: 健康检查成功
- **WHEN** 使用包含四个模型档位和 Milvus 地址的配置启动进程
- **THEN** 健康检查返回成功

### Requirement: 应用配置只描述模型和 Milvus
示例配置 MUST 包含编排、分析、研究方向和 embedding 四个模型档位，以及 Milvus 地址。应用配置 MUST NOT 包含 MinIO 地址或凭据。

#### Scenario: 示例配置没有 MinIO 凭据
- **WHEN** 读取应用示例配置
- **THEN** 其中有四个模型档位和 Milvus 地址，且没有 MinIO 地址或凭据

### Requirement: MinIO 只提供给 Milvus
compose MUST 启动 Milvus，并让 Milvus 依赖 etcd 和 MinIO。MinIO 地址 MUST 只出现在 Milvus 服务的配置中。

#### Scenario: 只有 Milvus 配置 MinIO 地址
- **WHEN** 查看 compose 中的服务配置
- **THEN** Milvus 依赖 etcd 和 MinIO，且只有 Milvus 服务配置了 MinIO 地址
