# Step 12 - 持久知识库 / 记忆卡 / 项目空间设计

## 1. 文档目标

这份设计文档用于回答 7 个能力如何在当前 CaiBao 仓库里落地：

1. 知识库
2. 记忆卡
3. 跨会话资料调用
4. 跨会话记忆
5. 回答收藏
6. 项目空间
7. 历史结论沉淀

重点不是重新发明一套新系统，而是基于当前仓库已经存在的能力演进：

1. 已有 `conversations`
2. 已有 `chat_history`
3. 已有 `documents -> document_chunks -> chunk_embeddings`
4. 已有 `rag_chat_service` 和 `retrieval_service`
5. 已有“同会话上下文记忆”和“会话级附件检索”

本设计的核心目标是：用最小改造成本，把系统从“会话级聊天 + 会话级附件 RAG”升级为“带项目边界的长期知识与记忆系统”。

## 2. 先给结论

建议采用下面这条主线：

1. 用 `project_spaces` 建立项目空间，作为跨会话数据隔离边界。
2. 用现有 `documents + chunks + embeddings` 承载长期可检索知识，不新起第二套知识检索栈。
3. 用 `memory_cards + memory_card_embeddings` 承载结构化、可编辑、可失效的跨会话记忆。
4. 用 `answer_favorites` 承载“收藏”这个轻操作，但默认不直接进入检索，避免把低质量回答当知识污染系统。
5. 用 `conclusions` 承载“历史结论沉淀”，并把有效结论同步为可检索的知识文档，复用现有 RAG 索引链路。
6. 聊天请求的上下文组装顺序改为：`当前会话 -> 记忆卡 -> 历史结论 -> 知识库`。

这条路径有两个明显好处：

1. 复用现有 `documents/chunks/embeddings`，知识库和历史结论几乎不需要重写检索底座。
2. 把“收藏”“记忆”“知识”“结论”分层，避免所有东西都混进同一个检索池。

## 3. 先统一概念

如果不先切清概念，后面实现会越做越乱。

### 3.1 项目空间 `project_space`

定义：一个项目或主题的长期工作容器。

一个项目空间下会包含：

1. 多个会话
2. 多个知识库文档
3. 多条记忆卡
4. 多条历史结论
5. 多条收藏回答

它是跨会话调用时默认的边界。

### 3.2 会话 `conversation`

定义：一次连续聊天上下文。

它负责：

1. 当前轮对话历史
2. 当前会话上传的临时附件
3. 最近几轮上下文记忆

它不应该天然拥有跨会话能力。

### 3.3 知识库 `knowledge library`

定义：用户明确发布到项目空间里的长期资料。

典型来源：

1. 手动上传的项目资料
2. 从会话附件发布
3. 从总结/结论生成的说明文档
4. 手动整理的笔记

特点：

1. 文档化
2. 可检索
3. 跨会话复用
4. 生命周期较长

### 3.4 记忆卡 `memory card`

定义：短小、结构化、可编辑的长期记忆单元。

典型内容：

1. 用户偏好
2. 项目约束
3. 长期目标
4. 稳定事实
5. 表达风格

特点：

1. 粒度小
2. 可人工确认
3. 可停用、可失效、可更新
4. 比知识库更适合“在回答前快速注入”

### 3.5 回答收藏 `favorite answer`

定义：用户认为有价值的回答快照。

它本质上是书签，不是事实真相。

特点：

1. 保存原始回答快照
2. 保留来源、上下文、时间
3. 可以二次转化为记忆卡、知识条目、结论
4. 默认不直接参与自动检索

### 3.6 历史结论 `conclusion`

定义：从历史对话中沉淀出来、经过确认的决策/结论/方案。

它和“收藏”最大的区别是：

1. 收藏是原样保存
2. 结论是二次整理后的结构化产物

它和“知识库”最大的区别是：

1. 知识库偏原始资料
2. 结论偏加工后的高价值认知资产

## 4. 当前仓库现状与问题

### 4.1 当前已有能力

1. `conversations` 已经实现会话隔离。
2. `chat_history` 已经保存消息、请求载荷、响应载荷。
3. `documents` 已经支持会话级附件上传、解析、切块、向量索引。
4. `rag_chat_service` 已经支持“会话消息 + 附件检索”混合回答。

### 4.2 当前不足

1. 没有项目空间，只有 `team_id/user_id` 和 `conversation_id`。
2. `documents` 只有“会话附件”语义，没有“长期知识库”语义。
3. 没有结构化跨会话记忆。
4. 没有回答收藏和历史结论沉淀。
5. `ChatSource` 只能表达文档块来源，不能表达记忆卡或结论来源。
6. 检索范围主要靠 `conversation_id`，缺少“项目级默认跨会话调用”。

## 5. 总体架构

建议把上下文分成 4 层：

1. `Session Layer`：当前会话消息和当前会话附件
2. `Memory Layer`：项目级或全局级记忆卡
3. `Conclusion Layer`：项目内已确认的历史结论
4. `Library Layer`：项目知识库文档

默认回答链路：

1. 先取当前会话最近 N 轮消息
2. 再召回适合当前问题的记忆卡
3. 再召回项目内有效历史结论
4. 最后召回项目知识库文档
5. 将多源结果融合排序后送给 LLM

默认优先级建议：

1. 当前会话
2. 记忆卡
3. 历史结论
4. 知识库

原因很简单：

1. 当前会话最贴近当下问题
2. 记忆卡最适合补偏好和稳定约束
3. 结论比原始知识更接近“可直接执行的判断”
4. 知识库通常体量更大、噪声更多

## 6. 推荐数据模型

### 6.1 新增表：`project_spaces`

这是本次设计的核心。

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `space_id` | `VARCHAR(36)` PK | 项目空间 ID |
| `team_id` | `VARCHAR(64)` FK | 账号边界 |
| `owner_user_id` | `VARCHAR(64)` FK | 创建人 |
| `name` | `VARCHAR(128)` | 空间名称 |
| `description` | `TEXT` nullable | 空间描述 |
| `status` | `VARCHAR(16)` | `active/archived/deleted` |
| `is_default` | `BOOLEAN` | 是否默认空间 |
| `default_scope_mode` | `VARCHAR(32)` | 默认上下文策略 |
| `created_at` | `DATETIME` | 创建时间 |
| `updated_at` | `DATETIME` | 更新时间 |

建议默认给每个用户创建一个“默认个人空间”。

### 6.2 改造表：`conversations`

新增字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `space_id` | `VARCHAR(36)` FK | 所属项目空间 |
| `scope_mode` | `VARCHAR(32)` | `session_only/project_hybrid/project_plus_global` |
| `last_message_at` | `DATETIME` | 会话排序更准确 |

说明：

1. 当前会话必须属于一个项目空间。
2. `scope_mode` 可以放会话级默认值，前端发送请求时允许临时覆盖。

### 6.3 改造表：`chat_history`

新增字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `space_id` | `VARCHAR(36)` FK | 所属项目空间 |
| `message_role` | `VARCHAR(16)` | `user/assistant/tool/system` |
| `sources_json` | `TEXT` nullable | 回答引用来源快照 |
| `favorite_count` | `INTEGER` | 收藏数缓存 |

说明：

1. 现在的 `chat_history` 更像 turn 记录，不是标准 message 表，但继续复用问题不大。
2. 增加 `sources_json` 后，可以把当时的召回证据存档，为后续收藏和结论沉淀提供依据。

### 6.4 改造表：`documents`

这是最关键的复用点。

建议在现有 `documents` 上扩展长期知识语义，而不是新建第二套知识库文档表。

新增字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `space_id` | `VARCHAR(36)` FK | 所属项目空间 |
| `visibility` | `VARCHAR(16)` | `conversation/space/global` |
| `asset_kind` | `VARCHAR(32)` | `attachment/knowledge_doc/manual_note/conclusion_note` |
| `origin_kind` | `VARCHAR(32)` nullable | `document/message/conclusion/favorite/manual` |
| `origin_id` | `VARCHAR(36)` nullable | 来源实体 ID |
| `summary` | `TEXT` nullable | 摘要 |
| `tags_json` | `TEXT` nullable | 标签 |
| `retrieval_enabled` | `BOOLEAN` | 是否参与自动检索 |
| `published_at` | `DATETIME` nullable | 发布到知识库时间 |
| `archived_at` | `DATETIME` nullable | 归档时间 |

推荐语义：

1. 当前上传到会话的附件：`visibility=conversation`，`asset_kind=attachment`
2. 发布到项目知识库的文档：`visibility=space`，`asset_kind=knowledge_doc`
3. 手动创建的项目笔记：`visibility=space`，`asset_kind=manual_note`
4. 从历史结论同步出的知识条目：`visibility=space`，`asset_kind=conclusion_note`

这样做的优势是：

1. 复用现有 `document_chunks`
2. 复用现有 `chunk_embeddings`
3. 复用现有上传、解析、切块、索引、预览链路

### 6.5 新增表：`memory_cards`

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `memory_id` | `VARCHAR(36)` PK | 记忆卡 ID |
| `team_id` | `VARCHAR(64)` FK | 账号边界 |
| `space_id` | `VARCHAR(36)` nullable | 项目级记忆可填，用户全局记忆可空 |
| `user_id` | `VARCHAR(64)` FK | 创建人 |
| `scope_level` | `VARCHAR(16)` | `space/global` |
| `category` | `VARCHAR(32)` | `preference/constraint/goal/fact/style` |
| `title` | `VARCHAR(128)` | 短标题 |
| `content` | `TEXT` | 记忆正文 |
| `summary` | `TEXT` nullable | 用于快速展示 |
| `weight` | `FLOAT` | 默认 `0.8`，用于融合排序 |
| `status` | `VARCHAR(16)` | `active/disabled/expired` |
| `confidence` | `FLOAT` | 来源可信度 |
| `source_message_id` | `VARCHAR(36)` nullable | 来源消息 |
| `source_document_id` | `VARCHAR(36)` nullable | 来源文档 |
| `expires_at` | `DATETIME` nullable | 过期时间 |
| `created_at` | `DATETIME` | 创建时间 |
| `updated_at` | `DATETIME` | 更新时间 |

### 6.6 新增表：`memory_card_embeddings`

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `embedding_id` | `VARCHAR(36)` PK | 主键 |
| `memory_id` | `VARCHAR(36)` FK | 记忆卡 ID |
| `team_id` | `VARCHAR(64)` FK | 账号边界 |
| `space_id` | `VARCHAR(36)` nullable | 空间边界 |
| `embedding_model` | `VARCHAR(64)` | 向量模型 |
| `vector_json` | `TEXT` | 向量 |
| `vector_dim` | `INTEGER` | 维度 |
| `created_at` | `DATETIME` | 创建时间 |
| `updated_at` | `DATETIME` | 更新时间 |

原因：

1. 记忆卡短小，不需要 chunk 粒度。
2. 一张卡一个向量足够。
3. 不应该把记忆卡强塞进 `documents`，否则编辑和失效控制会很别扭。

### 6.7 新增表：`answer_favorites`

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `favorite_id` | `VARCHAR(36)` PK | 主键 |
| `team_id` | `VARCHAR(64)` FK | 账号边界 |
| `space_id` | `VARCHAR(36)` FK | 所属项目空间 |
| `user_id` | `VARCHAR(64)` FK | 收藏人 |
| `conversation_id` | `VARCHAR(36)` FK | 来源会话 |
| `message_id` | `VARCHAR(36)` FK | 来源消息 |
| `title` | `VARCHAR(128)` | 收藏标题 |
| `question_text` | `TEXT` | 原问题快照 |
| `answer_text` | `TEXT` | 原回答快照 |
| `sources_json` | `TEXT` nullable | 回答来源快照 |
| `note` | `TEXT` nullable | 用户备注 |
| `tags_json` | `TEXT` nullable | 标签 |
| `is_promoted` | `BOOLEAN` | 是否已转化为知识或结论 |
| `created_at` | `DATETIME` | 创建时间 |

设计原则：

1. 收藏是轻量操作。
2. 收藏本身不自动进入知识库。
3. 收藏可以作为“待沉淀池”。

### 6.8 新增表：`conclusions`

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `conclusion_id` | `VARCHAR(36)` PK | 主键 |
| `team_id` | `VARCHAR(64)` FK | 账号边界 |
| `space_id` | `VARCHAR(36)` FK | 所属项目空间 |
| `user_id` | `VARCHAR(64)` FK | 创建人 |
| `title` | `VARCHAR(128)` | 结论标题 |
| `topic` | `VARCHAR(128)` | 主题 |
| `content` | `TEXT` | 结论正文 |
| `summary` | `TEXT` nullable | 摘要 |
| `status` | `VARCHAR(16)` | `draft/confirmed/effective/superseded/archived` |
| `confidence` | `FLOAT` | 可信度 |
| `effective_from` | `DATETIME` nullable | 生效时间 |
| `effective_to` | `DATETIME` nullable | 失效时间 |
| `source_message_id` | `VARCHAR(36)` nullable | 来源消息 |
| `source_favorite_id` | `VARCHAR(36)` nullable | 来源收藏 |
| `evidence_json` | `TEXT` nullable | 引用证据 |
| `tags_json` | `TEXT` nullable | 标签 |
| `doc_sync_document_id` | `VARCHAR(36)` nullable | 同步到 documents 的文档 ID |
| `created_at` | `DATETIME` | 创建时间 |
| `updated_at` | `DATETIME` | 更新时间 |

建议把“结论”作为显式资产，而不是隐含在消息里。

## 7. 为什么不用一张表解决所有问题

因为这 4 类数据天生不同：

1. 会话附件是原始资料
2. 记忆卡是结构化偏好/约束
3. 收藏是书签
4. 结论是经过确认的沉淀

如果把它们都塞进 `documents`：

1. 编辑体验会很差
2. 生命周期会混乱
3. 检索噪声会很高
4. 用户难以理解“为什么它会被召回”

所以推荐分层：

1. `documents` 负责长期可检索资料
2. `memory_cards` 负责结构化记忆
3. `answer_favorites` 负责收藏
4. `conclusions` 负责决策沉淀

## 8. 核心检索与编排策略

### 8.1 聊天请求新增上下文字段

建议在 `ChatAskRequest` 增加：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `space_id` | `str` | 当前项目空间 |
| `scope_mode` | `str` | 上下文策略 |
| `include_memory` | `bool` | 是否启用记忆卡 |
| `include_conclusions` | `bool` | 是否启用历史结论 |
| `include_library` | `bool` | 是否启用知识库 |

推荐默认值：

1. `space_id` 必填
2. `scope_mode=project_hybrid`
3. `include_memory=true`
4. `include_conclusions=true`
5. `include_library=true`

### 8.2 新的回答编排流程

建议 `rag_chat_service.ask()` 改造成下面的流程：

1. 校验 `team_id/user_id/space_id/conversation_id`
2. 取当前会话最近 N 轮消息
3. 取当前会话附件
4. 召回匹配的记忆卡
5. 召回匹配的历史结论
6. 召回知识库文档块
7. 做融合排序
8. 在 token 预算内打包上下文
9. 调用 LLM 生成回答
10. 把来源快照写入 `chat_history.sources_json`

### 8.3 多源召回建议

#### 当前会话

继续使用现在的逻辑：

1. 最近 N 轮问答
2. 当前会话附件

#### 记忆卡

新增 `MemoryService.search_cards()`：

1. 对问题做 embedding
2. 对激活状态的记忆卡做相似度计算
3. 返回 top_k

记忆卡建议限制很严：

1. 默认只取 3 到 5 条
2. 单条卡片建议不超过 500 字

#### 历史结论

历史结论有两种实现方式：

1. 直接给 `conclusions` 做独立向量检索
2. 把有效结论同步成 `documents`，复用现有检索

推荐当前仓库采用第 2 种：

1. `conclusions.status in ('confirmed', 'effective')`
2. 自动生成一条 `documents` 记录
3. `asset_kind=conclusion_note`
4. `visibility=space`
5. 走现有 chunk/index/search 链路

这样可大幅减少改造范围。

#### 知识库

继续使用现有 `retrieval_service.search_chunks()`，但增加过滤条件：

1. `space_id = current_space_id`
2. `visibility in ('space', 'global')`
3. `retrieval_enabled = true`
4. `status = 'ready'`

### 8.4 融合排序建议

建议引入统一分数：

`final_score = semantic_score * source_weight * freshness_weight * confidence_weight`

建议权重：

1. 当前会话附件：`1.00`
2. 记忆卡：`0.95`
3. 历史结论：`0.90`
4. 知识库：`0.80`

建议额外规则：

1. 过期记忆卡不参与召回
2. `superseded/archived` 结论不参与召回
3. 收藏回答默认不参与召回
4. 被用户手动 pin 的记忆卡可小幅加权

### 8.5 来源解释必须升级

当前 `ChatSource` 只够描述文档块来源，后续必须扩展。

建议新增字段：

| 字段 | 说明 |
| --- | --- |
| `source_type` | `conversation_document/memory_card/conclusion/library_document` |
| `source_id` | 来源实体 ID |
| `title` | 来源标题 |
| `space_id` | 所属项目空间 |
| `reason` | 为什么被召回 |

这会直接影响用户信任感。

## 9. 7 个能力分别怎么落地

### 9.1 知识库

落地方式：

1. 扩展 `documents` 为长期知识资产容器。
2. 增加“发布到项目知识库”动作。
3. 知识库文档默认 `conversation_id = null`，`space_id` 必填。
4. 所有知识库文档继续走现有切块和向量索引。

最关键的产品动作：

1. 会话附件可一键发布到知识库
2. 手动创建知识笔记
3. 结论可同步为知识条目

### 9.2 记忆卡

落地方式：

1. 新增 `memory_cards`
2. 新增 `memory_card_embeddings`
3. 在回答页支持“记住这条”
4. 支持系统建议生成，但默认需要用户确认

建议记忆卡模板：

1. 偏好：`以后默认用中文回答`
2. 约束：`本项目只能使用 FastAPI + SQLite`
3. 目标：`未来 2 周内优先完成移动端上传链路`
4. 事实：`当前默认 embedding 模型是 xxx`

### 9.3 跨会话资料调用

落地方式：

1. 当前会话属于某个 `space_id`
2. 当 `scope_mode != session_only` 时，允许检索同空间下 `visibility=space` 的文档
3. 默认不允许跨空间自动检索

这点非常重要：

1. “跨会话”默认应该是“同项目空间跨会话”
2. 不是“所有历史会话自动互通”

### 9.4 跨会话记忆

落地方式：

1. 当前会话进入回答前，先召回 `space_id` 下的激活记忆卡
2. 可选再召回 `global` 级记忆卡
3. 会话级消息历史仍保持短期上下文，不直接混入长期记忆池

建议分层：

1. 全局记忆：表达习惯、身份偏好
2. 项目记忆：项目约束、阶段目标、术语约定

### 9.5 回答收藏

落地方式：

1. 助手回答右上角支持“收藏”
2. 收藏保存到 `answer_favorites`
3. 支持收藏后追加备注和标签
4. 支持从收藏一键转化为“记忆卡”或“历史结论”

关键原则：

1. 收藏默认不直接参与自动检索
2. 收藏是候选资产，不是已确认知识

### 9.6 项目空间

落地方式：

1. 新增 `project_spaces`
2. 所有 `conversation/document/chat_history/memory/conclusion/favorite` 都挂到 `space_id`
3. 前端左侧导航切换“空间 -> 会话”

项目空间承担的不是视觉分组，而是检索隔离边界。

### 9.7 历史结论沉淀

落地方式：

1. 对回答或收藏执行“沉淀为结论”
2. 进入结论编辑页，补标题、结论正文、有效期、证据
3. 状态从 `draft` 到 `confirmed/effective`
4. 生效后同步为可检索文档

沉淀动作建议提供 3 种入口：

1. 从一条回答直接沉淀
2. 从收藏列表批量沉淀
3. 从系统建议列表确认沉淀

## 10. 关键写入链路

### 10.1 会话附件发布到知识库

流程建议：

1. 用户在附件菜单点击“发布到知识库”
2. 后端复制一条 `documents` 记录
3. 新记录设置 `visibility=space`
4. 新记录设置 `asset_kind=knowledge_doc`
5. `origin_kind=document`
6. `origin_id=<原 document_id>`
7. 沿用原始文件存储或共享 `storage_key`
8. 异步执行 chunk/index

这样做优于直接改原记录，因为：

1. 会话附件和长期知识语义不同
2. 删除会话时不应该误删知识库条目

### 10.2 回答收藏

流程建议：

1. 用户点击“收藏”
2. 从 `chat_history` 取问题、回答、来源快照
3. 写入 `answer_favorites`
4. 不做索引

### 10.3 收藏转记忆卡

流程建议：

1. 用户从收藏点击“转为记忆卡”
2. 弹出表单选择类别、范围、权重
3. 写入 `memory_cards`
4. 异步写入 `memory_card_embeddings`

### 10.4 收藏或回答沉淀为结论

流程建议：

1. 用户点击“沉淀为结论”
2. 系统先生成草稿摘要
3. 用户确认后写入 `conclusions`
4. 当状态到 `confirmed/effective` 时，同步一份 `documents`
5. 异步执行 chunk/index

## 11. API 设计建议

### 11.1 项目空间

1. `POST /api/v1/spaces`
2. `GET /api/v1/spaces`
3. `PATCH /api/v1/spaces/{space_id}`
4. `DELETE /api/v1/spaces/{space_id}`

### 11.2 会话

1. `POST /api/v1/conversations`
2. `GET /api/v1/conversations?space_id=...`
3. `PATCH /api/v1/conversations/{conversation_id}`
4. `DELETE /api/v1/conversations/{conversation_id}`

### 11.3 知识库

1. `POST /api/v1/library/documents/import`
2. `POST /api/v1/library/documents/upload`
3. `POST /api/v1/library/documents/publish-from-conversation`
4. `GET /api/v1/library/documents?space_id=...`
5. `PATCH /api/v1/library/documents/{document_id}`
6. `DELETE /api/v1/library/documents/{document_id}`

### 11.4 记忆卡

1. `POST /api/v1/memory/cards`
2. `GET /api/v1/memory/cards?space_id=...`
3. `PATCH /api/v1/memory/cards/{memory_id}`
4. `DELETE /api/v1/memory/cards/{memory_id}`
5. `POST /api/v1/memory/cards/suggest-from-message`

### 11.5 收藏

1. `POST /api/v1/favorites/answers`
2. `GET /api/v1/favorites/answers?space_id=...`
3. `PATCH /api/v1/favorites/answers/{favorite_id}`
4. `DELETE /api/v1/favorites/answers/{favorite_id}`
5. `POST /api/v1/favorites/answers/{favorite_id}/promote-to-memory`
6. `POST /api/v1/favorites/answers/{favorite_id}/promote-to-conclusion`

### 11.6 历史结论

1. `POST /api/v1/conclusions`
2. `GET /api/v1/conclusions?space_id=...`
3. `PATCH /api/v1/conclusions/{conclusion_id}`
4. `POST /api/v1/conclusions/{conclusion_id}/confirm`
5. `POST /api/v1/conclusions/{conclusion_id}/archive`

### 11.7 聊天接口

扩展 `POST /api/v1/chat/ask`

新增建议字段：

1. `space_id`
2. `scope_mode`
3. `include_memory`
4. `include_conclusions`
5. `include_library`

## 12. 前端交互建议

### 12.1 左侧导航改为两层

1. 顶层：项目空间列表
2. 二层：当前空间下的会话列表

### 12.2 会话主界面增加上下文范围提示

输入框上方或旁边展示：

1. 当前会话
2. 当前项目空间
3. 全局记忆

用户必须知道这次回答会不会跨会话。

### 12.3 回答操作菜单

每条助手回答建议增加：

1. 收藏
2. 生成记忆卡
3. 沉淀为结论
4. 发布为知识笔记

### 12.4 空间资产面板

建议右侧或独立页提供 4 个 Tab：

1. 知识库
2. 记忆卡
3. 历史结论
4. 收藏

### 12.5 来源解释 UI

回答下方不仅展示“来自哪些文档”，还要展示：

1. 来自哪张记忆卡
2. 来自哪条历史结论
3. 来自哪个知识文档

## 13. 工程实现建议

### 13.1 不建议继续用纯手写轻量迁移硬撑

当前仓库在 `app/db/session.py` 里用 `ALTER TABLE` 做 best-effort migration，这在 1 到 2 次小升级时还能接受。

但这次新增的实体和索引明显更多，建议：

1. 引入 Alembic 管理 schema 迁移
2. 保留 `Base.metadata.create_all()` 仅用于全新开发库
3. 将生产和真实测试用例统一迁移到版本化 migration

### 13.2 服务层拆分建议

建议新增服务：

1. `SpaceService`
2. `MemoryService`
3. `FavoriteService`
4. `ConclusionService`
5. `ContextAssemblyService`

其中：

1. `RagChatService` 负责对话入口
2. `ContextAssemblyService` 负责多源召回与上下文组装
3. `RetrievalService` 继续负责文档块向量检索

### 13.3 避免一次性重写 `chat_history`

当前 `chat_history` 不是标准 message 表，但短期内没必要为了“架构洁癖”整体推翻。

建议：

1. 保留 `chat_history` 作为 turn 存储
2. 逐步增加 `space_id/sources_json/message_role`
3. 如果以后要做 streaming、tool call、message versioning，再单独演进为 `messages`

## 14. 分阶段实施建议

### Phase 1：先把项目空间和知识库立起来

目标：

1. 新增 `project_spaces`
2. `conversations/documents/chat_history` 增加 `space_id`
3. `documents` 增加 `visibility/asset_kind/retrieval_enabled`
4. 增加“发布到知识库”
5. `chat/ask` 支持按 `space_id` 检索知识库

收益：

1. 先解决“跨会话资料调用”
2. 先建立“项目空间边界”

### Phase 2：补记忆卡

目标：

1. 新增 `memory_cards`
2. 新增 `memory_card_embeddings`
3. 回答页支持“记住这条”
4. `chat/ask` 支持召回记忆卡

收益：

1. 解决“跨会话记忆”
2. 解决偏好和长期约束注入

### Phase 3：补收藏和结论沉淀

目标：

1. 新增 `answer_favorites`
2. 新增 `conclusions`
3. 收藏可转记忆卡和结论
4. 结论同步为可检索知识文档

收益：

1. 解决“回答收藏”
2. 解决“历史结论沉淀”

### Phase 4：做系统建议与自动化

目标：

1. 在回答后自动建议“是否沉淀为记忆卡/结论”
2. 定期检测重复结论与过期记忆
3. 做结论版本替换和归档

## 15. 关键风险与控制

### 15.1 风险：跨项目串数

控制：

1. 所有长期资产默认必须带 `space_id`
2. 默认只允许检索当前 `space_id`
3. 跨空间调用必须显式操作

### 15.2 风险：低质量回答污染知识库

控制：

1. 收藏不自动入库
2. 回答沉淀为结论必须经过确认
3. 结论进入检索前需状态达到 `confirmed/effective`

### 15.3 风险：上下文过载

控制：

1. 记忆卡数量严格限制
2. 结论和知识文档都要做 top_k
3. 统一 token budget 管理

### 15.4 风险：用户不理解来源

控制：

1. 扩展 `ChatSource`
2. 回答后展示来源类型
3. 支持一键关闭跨会话上下文

## 16. 最推荐的落地顺序

如果只按投入产出比排优先级，建议顺序如下：

1. `project_spaces`
2. `documents` 扩展为知识库资产
3. `chat/ask` 支持项目级检索
4. `memory_cards`
5. `answer_favorites`
6. `conclusions`

一句话总结：

先解决“项目边界”和“跨会话资料复用”，再解决“跨会话记忆”，最后做“收藏”和“历史结论沉淀”。这条路径最符合当前仓库的演进成本，也最容易做出用户能立即感知到的价值。
