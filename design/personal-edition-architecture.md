# CaiBao 个人版架构设计（会话隔离 + 可控跨会话上下文）

## 1. 目标与范围

本设计用于将当前 CaiBao 从“团队共享知识库”形态，演进为“个人智能助手（小豆包）”形态。

目标：

1. 默认体验与豆包/GPT 一致：打开即能对话，无需先上传文件
2. 文件默认仅当前会话可见，避免不同对话互相污染
3. 支持像 Gemini 一样跨会话获取上下文，但必须可控、可解释、可撤回
4. 保持实现简洁：主路径清晰，复杂能力通过显式开关启用

非目标（本阶段不做）：

1. 多租户企业权限体系（组织、角色、审计）
2. 复杂协作场景（多人共享会话、会话转派）

---

## 2. 产品原则

1. 默认隔离：不跨会话自动读取历史全文
2. 显式桥接：跨会话只能通过“记忆卡片 / 资料库”引入
3. 来源可解释：回答可标注来自会话、记忆、资料库
4. 用户可控：支持开关、删除、导出
5. 行为可预测：同样输入在同样开关下有稳定行为

---

## 3. 上下文三层模型

### 3.1 会话层（Session Scope）

定义：当前会话内消息、附件、临时索引。  
特性：

1. 强隔离（默认）
2. 生命周期与会话一致
3. 优先级最高（当前问题优先看当前会话）

### 3.2 记忆层（Memory Scope）

定义：结构化“记忆卡片”（偏好、长期目标、约束、事实）。  
来源：

1. 用户手动“记住这条”
2. 系统建议并经用户确认写入

特性：

1. 跨会话可用
2. 可编辑、可删除、可停用
3. 有权重与过期策略

### 3.3 知识层（Library Scope）

定义：用户主动发布到“资料库”的文档。  
特性：

1. 跨会话复用
2. 可按标签/空间检索
3. 不与会话临时文件混用

---

## 4. 请求编排策略（核心）

`chat/ask` 建议流程：

1. 读取会话配置（`scope_mode`）
2. 构造上下文候选：
   1. `session_only`：仅会话层
   2. `session_plus_memory`：会话层 + 记忆层
   3. `session_plus_library`：会话层 + 资料库
   4. `hybrid`：会话层 + 记忆层 + 资料库
3. 判断是否存在可检索索引：
   1. 有索引：RAG 路径
   2. 无索引：普通对话路径
4. 返回答案 + `sources`（来源元数据）

设计重点：  
主路径应是“可直接聊天”，RAG 是增强能力，不是前置条件。

---

## 5. 数据模型设计（个人版）

下表为建议新增/改造模型（SQLAlchemy 对应）：

### 5.1 `accounts`（个人账户）

字段建议：

1. `account_id`（PK）
2. `display_name`
3. `email`（可空，后续接登录）
4. `created_at`
5. `updated_at`

### 5.2 `conversations`（会话）

字段建议：

1. `conversation_id`（PK）
2. `account_id`（FK -> accounts）
3. `title`
4. `scope_mode`（`session_only/session_plus_memory/session_plus_library/hybrid`）
5. `status`（`active/archived/deleted`）
6. `created_at`
7. `updated_at`

### 5.3 `messages`（消息）

字段建议：

1. `message_id`（PK）
2. `conversation_id`（FK）
3. `role`（`user/assistant/system/tool`）
4. `channel`（`ask/echo/action`）
5. `content`
6. `request_payload_json`
7. `response_payload_json`
8. `sources_json`（来源列表，可空）
9. `created_at`

### 5.4 `conversation_documents`（会话文件）

字段建议：

1. `document_id`（PK）
2. `account_id`（FK）
3. `conversation_id`（FK，非空）
4. `source_name`
5. `content_type`
6. `content`
7. `visibility`（固定 `conversation`）
8. `created_at`

### 5.5 `library_documents`（资料库文件）

字段建议：

1. `library_doc_id`（PK）
2. `account_id`（FK）
3. `source_name`
4. `content_type`
5. `content`
6. `tags_json`
7. `created_at`

### 5.6 `memory_cards`（记忆卡片）

字段建议：

1. `memory_id`（PK）
2. `account_id`（FK）
3. `category`（`preference/goal/constraint/fact`）
4. `content`
5. `weight`（0~1）
6. `status`（`active/disabled`）
7. `source_message_id`（可空）
8. `created_at`
9. `updated_at`

### 5.7 索引表

建议按“作用域”拆分，避免混检：

1. `conversation_chunk_embeddings`
2. `library_chunk_embeddings`
3. （可选）`memory_embeddings`

---

## 6. API 设计（建议）

### 6.1 会话

1. `POST /api/v1/conversations`
2. `GET /api/v1/conversations`
3. `GET /api/v1/conversations/{conversation_id}`
4. `PATCH /api/v1/conversations/{conversation_id}`（改标题、scope）
5. `DELETE /api/v1/conversations/{conversation_id}`（软删除）

### 6.2 消息

1. `GET /api/v1/conversations/{conversation_id}/messages`
2. `DELETE /api/v1/messages/{message_id}`

### 6.3 会话文件（隔离）

1. `POST /api/v1/conversations/{conversation_id}/documents/import`
2. `GET /api/v1/conversations/{conversation_id}/documents`
3. `DELETE /api/v1/conversations/{conversation_id}/documents/{document_id}`
4. `POST /api/v1/conversations/{conversation_id}/retrieval/index`

### 6.4 资料库

1. `POST /api/v1/library/documents/import`
2. `GET /api/v1/library/documents`
3. `DELETE /api/v1/library/documents/{library_doc_id}`

### 6.5 记忆

1. `POST /api/v1/memory/cards`
2. `GET /api/v1/memory/cards`
3. `PATCH /api/v1/memory/cards/{memory_id}`
4. `DELETE /api/v1/memory/cards/{memory_id}`

### 6.6 聊天入口

`POST /api/v1/chat/ask`

请求建议：

1. `account_id`
2. `conversation_id`
3. `question`
4. `model`
5. `scope_mode`（可选，默认取会话配置）

响应建议：

1. `answer`
2. `mode`（`chat/rag`）
3. `sources`（数组）
4. `hits`（检索命中，可能为空）

---

## 7. 前端交互设计（个人版）

### 7.1 左侧会话列表

1. 新建会话
2. 重命名
3. 删除会话（带二次确认）
4. 展示最近更新时间

### 7.2 中央聊天区

1. 默认可直接对话
2. 输入框旁显示上下文范围开关：
   1. 仅当前会话
   2. 当前会话 + 记忆
   3. 当前会话 + 资料库
   4. 混合
3. 回答下方显示来源标签（可折叠）

### 7.3 文件上传区

1. 默认上传到当前会话（隔离）
2. 提供“发布到资料库”按钮（显式跨会话）

### 7.4 消息菜单

1. 删除该条消息
2. 记住这条（生成 memory card）
3. 取消记忆（若已有关联）

---

## 8. 删除与生命周期策略

### 8.1 软删除优先

1. 会话删除：`status=deleted`
2. 消息删除：逻辑删除或物理删除（二选一，推荐逻辑删除 + 异步清理）
3. 文档删除：删除原文 + chunk + embedding

### 8.2 级联关系

删除会话时应级联删除：

1. `messages`
2. `conversation_documents`
3. `conversation_chunks`
4. `conversation_embeddings`

### 8.3 审计与恢复

1. 软删除保留 7~30 天可恢复（可选）
2. 彻底清理走异步任务

---

## 9. 检索与排序策略（简化可落地）

召回顺序建议：

1. 会话文档命中（高优先）
2. 记忆命中
3. 资料库命中（低于会话）

混排打分建议（示意）：

`final_score = semantic_score * source_weight * freshness_weight`

其中：

1. `source_weight`：会话 1.0，记忆 0.85，资料库 0.75
2. `freshness_weight`：新内容略加权，避免旧知识长期垄断

---

## 10. 迁移方案（从当前版本到个人版）

### Phase 1（最小改造）

1. 保留现有 `team/user`，新增 `conversation` 概念
2. `chat_history` 增加 `conversation_id`
3. 文档增加 `conversation_id`，默认只查当前会话
4. 前端支持会话新建与删除

### Phase 2（个人版成型）

1. 引入 `account` 替代 `team`
2. 拆分会话文档与资料库文档
3. 上线 memory cards

### Phase 3（Gemini 风格增强）

1. 上下文来源解释 UI
2. 记忆建议写入
3. 跨会话开关与权限提示完善

---

## 11. 风险与控制

1. 风险：跨会话误召回导致“串台”  
控制：默认 `session_only`，来源标签可见
2. 风险：数据膨胀（消息、embedding 激增）  
控制：TTL、归档、异步压缩
3. 风险：用户不理解“为什么回答这样”  
控制：可解释来源 + 一键关闭跨会话

---

## 12. 成功指标（建议）

1. 首次提问成功率（无上传场景）> 99%
2. 会话隔离投诉率显著下降
3. 跨会话功能开启率与保留率
4. 来源解释点击率（衡量可解释性价值）

---

## 13. 实现建议（工程优先级）

按投入产出比，推荐顺序：

1. 会话模型 + 会话级文档隔离
2. 会话/消息删除接口
3. scope 开关（session_only/hybrid）
4. 记忆卡片
5. 资料库发布与复用

> 结论：先把“默认隔离 + 能直接聊 + 可删除”做好，再做跨会话智能，是成本最低且体验最稳的路径。

