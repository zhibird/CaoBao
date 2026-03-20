# v0.6.0 - 2026-03-19

## what's next

1. 进行mock和真实模型的RAG性能评估。
2. 完善用户自定义模型功能。

## 版本概览

本版本聚焦三件事：

1. RAG 检索链路正式支持真实 embedding（非 mock）并可安全重建索引。
2. 落地可复现的真实场景评测最小集（A/B/C 共 50 题）。
3. 前端模型策略升级：`default` 走 `.env`，`none` 强制 mock；新增向量模型可配置。

## 新增内容

1. 真实 embedding 配置项与运行时逻辑（provider/base_url/api_key/model/batch）。
2. embedding 模型账号隔离配置接口（按 `team_id + user_id` 管理）。
3. 前端新增“向量模型”下拉与自定义入口。
4. 真实场景评测脚本与语料数据集（Recall@1/3/5、命中来源、失败 Top10、对比报告）。

## 主要变更

1. `EmbeddingService` 升级为双模式：
   `mock`（hashing）与 `real`（调用 `/embeddings`，支持批量、响应校验、错误处理）。
2. 检索链路升级：
   支持批量向量化写入、`rebuild` 重建索引、检索维度一致性校验（不一致返回 400）。
3. 聊天模型默认行为调整：
   前端 `default` 不再走 `echo`，改为走 `/chat/ask` 并读取 `.env`；
   `none` 走 `/chat/ask` 且后端强制 mock。
4. 检索请求支持会话用户选择 embedding 模型：
   `retrieval/index`、`retrieval/search`、`chat/ask` 与历史重编辑链路均可带 `embedding_model`。

## 验证结果

1. Python 回归测试通过：`36 passed`。
2. 前端脚本语法检查通过：`node --check app/web/app.js`。
3. 真实场景评测链路（prepare/eval/compare）已可执行。

