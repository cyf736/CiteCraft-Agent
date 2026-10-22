# Design

## Context

`backend-shell` 提供 embedding 档位和 Milvus 的部署方式。arxiv-agent 已有切块、PDF 提取、arXiv 获取和 Milvus 写入实现，可按本变更的记录字段改编。见 `proposal.md` 的 Why。工具返回论文结果，不调用 agent。

## Goals / Non-Goals

**Goals:**

- 用同一存储接口支持内存实现和 Milvus 实现。
- 用相似度阈值区分命中与未命中。
- 未命中时完成有限数量的 arXiv 入库。

**Non-Goals:**

- 不创建主图节点，不写入会话状态。
- 不保存 PDF 文件，不让工具连接 MinIO。

## Decisions

### 1. 一条记录是一个切块

集合名为 `citecraft_chunks`。字段为 `paper_id`、`title`、`chunk_index`、`chunk_text`、`embedding`、`arxiv_url`、`text_source`。`text_source` 取 `body` 或 `abstract`。切块大小 512、重叠 50。默认向量维度 1536，与 embedding 档位一致。

### 2. 阈值决定是否访问 arXiv

查询先取近邻切块。切块余弦相似度达到 `retrieval_min_score` 时，其所在论文算命中。初始阈值为 0.5。没有任何论文达到阈值，或集合为空，才访问 arXiv。一次最多新入库 5 篇，由 `max_new_papers` 配置。

备选是库非空就不再访问 arXiv。近邻查询在库非空时总会返回若干条，未命中将无法发生。

### 3. 入库来源

PDF 文本提取成功则写入 `body`，否则用摘要写入 `abstract`。失败的论文不进入成功结果。已成功写入的旧切块保留。

工具通过 `backend-shell` 的 embedding 档位生成向量，通过 Milvus 地址连接向量库。测试使用内存实现，不要求启动 Milvus。

## Risks / Trade-offs

- [阈值 0.5 把相关论文判成未命中，或把弱相关论文判成命中] → 阈值可配置，结果带分数。agent 图可以换查询参数再次调用。
- [PDF 提取失败只留下摘要] → `text_source=abstract`，分析变更据此标明正文缺失。

## Migration Plan

在 `backend-shell` 的配置上追加 `retrieval_min_score` 和 `max_new_papers`。首次真实写入时创建 `citecraft_chunks`。回滚时删除该集合，不影响其他集合。

## Open Questions

- 阈值 0.5 可以在真实查询后调整，不改变“低于阈值即未命中”的规则。
