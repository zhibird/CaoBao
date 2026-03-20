# v0.7.1 - 2026-03-20

## 版本概览（what's fix?）

本版本聚焦修复两类核心问题：  
1. `default` 模式未正确读取根目录 `.env`（聊天模型与向量模型都受影响）。  
2. 文档已导入/分块但索引失败，导致会话无法稳定走 RAG 上下文链路。  

同时补齐了索引链路的稳定性能力（错误透传、分批控制、超时自适应重试）。

## 主要修复

1. `default` 行为修正为“优先使用 `.env`”
   - 聊天模型：
     - `default` => 使用 `.env` 的 LLM 配置
     - `none` => 强制 mock
   - 向量模型：
     - `default` => 使用 `.env` 的 embedding 配置
     - `mock`/`none` => 使用 hashing mock

2. RAG 链路修正
   - 修复 `default` 被当作字面模型名向上游透传的问题（避免错误请求）。
   - 修复检索端 embedding 运行时选择逻辑：
     - `default` 不再误走 mock；
     - 仅 `mock/none` 走 mock 向量。

3. Embedding 索引稳定性增强
   - 透传上游 4xx/5xx 响应体（便于定位真实原因）。
   - 增加 provider 兼容：
     - DashScope 自动限制批量不超过 10。
   - 增加超时自愈：
     - 批量请求超时后自动降批重试（直到单条）；
     - 单条请求支持重试，超过上限再返回明确错误。

4. 前端导入体验修复
   - 导入、分块、索引改为分阶段结果提示：
     - “导入成功但分块失败”
     - “导入+分块成功但索引失败”
   - 向量模型下拉新增显式 `mock` 选项，`default` 标签改为 `.env` 语义。
   - 静态资源版本号更新，避免浏览器缓存导致旧前端逻辑继续生效。

5. 配置热更新
   - 依赖注入层在创建 LLM/Embedding 服务时重新加载配置，减少“改了 `.env` 但进程仍使用旧配置”的问题。

## 验证结果

1. 全量测试通过：`40 passed`。  
2. 语法检查通过：`node --check app/web/app.js`。  
3. 本地索引链路烟测通过：`/api/v1/retrieval/index` 返回 200，`indexed_chunks` 正常。

## 已实现

1. 修复 `default/.env` 与 mock 分流逻辑（LLM + RAG）  
   `app/services/llm_service.py`  
   `app/services/rag_chat_service.py`  
   `app/services/retrieval_service.py`

2. 修复 embedding 运行时与配置保留字处理  
   `app/services/embedding_model_service.py`  
   `app/services/embedding_service.py`

3. 增强 embedding 索引鲁棒性（错误透传、DashScope 批量限制、超时降批重试）  
   `app/services/embedding_service.py`

4. 前端向量模型选择与导入流程提示优化  
   `app/web/app.js`  
   `app/web/index.html`

5. 配置热加载接入依赖注入  
   `app/api/deps.py`

6. 测试与回归补齐  
   `tests/test_llm_service.py`  
   `tests/test_embedding_service.py`  
   `tests/test_embedding_model.py`  
   `tests/conftest.py`
