# Tasks

## 1. 切块与存储

- [ ] 1.1 在 `backend-shell` 的示例配置中追加 `retrieval_min_score=0.5` 和 `max_new_papers=5`。验证：示例配置含这两个键，且仍然没有 MinIO 地址或凭据。
- [ ] 1.2 实现 512 字、重叠 50 的切块，以及包含 `paper_id`、`title`、`chunk_index`、`chunk_text`、`embedding`、`arxiv_url`、`text_source` 的记录。验证：测试确认长文本被拆开，且 `text_source` 可标为 `body` 或 `abstract`。
- [ ] 1.3 实现存储接口和内存实现。相似度达到 `retrieval_min_score` 才算命中，并按论文分组。验证：低于 0.5 的切块不算命中；达到阈值的切块返回论文标识、题名和切块文本。
- [ ] 1.4 实现 Milvus 集合 `citecraft_chunks` 的同一接口，默认维度 1536。验证：不连接真实 Milvus 的映射测试确认写入字段和按 `paper_id` 读取的字段与存储接口一致。

## 2. arXiv 获取

- [ ] 2.1 实现检索工具：先查存储，有命中论文时不访问 arXiv。验证：预置高分切块的测试确认结果含论文标识、切块、`text_source` 和“已入库”来源，不含研究空白、技术路线或创新点，且 arXiv 客户端未被调用。
- [ ] 2.2 未命中时从 arXiv 获取并入库，数量不超过 `max_new_papers`。PDF 文本成功记为 `body`，失败记为 `abstract`。验证：伪造 arXiv 与 PDF 提取的测试覆盖正文入库、摘要入库，以及获取失败时不产生成功论文且旧切块仍可命中。

## Workflow follow-up

- 实现完成并经过复查后，再归档本次变更。
- 归档后确认主规格包含 `paper-retrieval`。
