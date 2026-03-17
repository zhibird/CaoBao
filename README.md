# CaiBao

这是一个面向新手、从零开始的最小版项目。目标不是一次做成“大而全”的系统，而是先做出一个能跑通的 MVP（CaiBao），再一层层补能力。

## 1. 最小版能力

1. 用户 / 团队配置
2. 聊天入口
3. 文档导入
4. 文档切分
5. 向量索引与检索
6. RAG 问答
7. 工具插件（后续）
8. 聊天记录（后续）
9. Docker 部署（后续）

## 2. 当前完成

1. `/api/v1/teams`、`/api/v1/users` 配置管理
2. `/api/v1/documents/import` 文档导入
3. `/api/v1/documents/{id}/chunk` 文档切分
4. `/api/v1/retrieval/index` 向量索引
5. `/api/v1/retrieval/search` TopK 检索
6. `/api/v1/chat/ask` RAG 问答（默认 mock LLM，可切换真实 LLM）

## 3. 下一步

1. 在 `chat/ask` 中加入更严格的引用/来源格式
2. 接入 1-2 个工具插件
3. 保存聊天记录并做 Docker 部署

## 4. 学习文档

1. `docs/step-01-module-map.md`
2. `docs/step-02-run-locally.md`
3. `docs/step-03-team-user-config.md`
4. `docs/step-04-document-import.md`
5. `docs/step-04-chunking.md`
6. `docs/step-05-retrieval-index-search.md`
7. `docs/step-05-rag-chat.md`