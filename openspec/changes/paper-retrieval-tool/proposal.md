# Proposal

## Why

检索节点需要一个可单独测试的工具：先查已入库切块，没有命中再从 arXiv 获取并入库。把这个工具留在 agent 图里，会让图的变更同时承担切块、向量库和 arXiv 访问。

## What Changes

- 提供检索工具。调用方传入查询参数，工具返回论文结果或失败。
- 先查询已入库切块。相似度达到配置阈值才算命中；有命中时不再访问 arXiv。
- 没有命中时从 arXiv 获取论文。PDF 文本可用则入库正文切块，否则入库摘要切块。一次最多新入库 5 篇。
- 每条入库记录是一个切块及其向量和论文元数据，不保存整篇论文文件。
- 获取或入库失败时不产生成功结果，已有切块仍可查询。

工具不决定下一步调用哪个 agent，也不进入主图。它依赖 `backend-shell` 的 embedding 档位和 Milvus 运行环境。

## Capabilities

### New Capabilities

- `paper-retrieval`: 按查询参数做切块检索，并在未命中时从 arXiv 获取、切块和入库

### Modified Capabilities

无。`paper-retrieval` 尚未归档到主规格。

## Impact

- 新增切块、存储接口、内存实现、Milvus 实现和 arXiv 获取。
- 示例配置追加最低相似度和单次新入库篇数。
- `multi-agent-research-workflow` 的检索节点调用这个工具，不重复实现入库。
