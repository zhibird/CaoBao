# v0.4.0 - 2026-03-18

## 版本概览

本版本完成了“用户可在前端配置大模型并按账号隔离使用”的核心能力：

1. 新增账号级模型配置管理（`API Key + Base URL + Model`）。
2. 前端模型选择支持 `default` 基础模式与自定义模型新增。
3. 聊天链路接入账号模型配置，并保证不同账号互相隔离。

## 新增内容

1. 新增 `llm_model_configs` 数据表，用于存储账号级模型配置。
2. 新增模型配置接口：`GET/POST/DELETE /api/v1/llm/models`。
3. 新增模型配置服务层，提供 upsert/list/delete/runtime resolve 能力。
4. 新增模型隔离与模型未配置校验测试用例。

## 主要变更

1. `RagChatService` 在 `chat/ask` 时按 `team_id + user_id + model_name` 解析模型运行配置。
2. `LLMService` 支持按请求覆盖 `base_url/api_key`，可直接调用用户配置的大模型。
3. 前端模型选择改为账号隔离存储：`selectedModel:<team_id>:<user_id>`。
4. 当前账号无模型配置时，前端默认显示 `default`，发送消息仅走 `chat/echo` 基础模式。

## 兼容性说明

1. 本次为新增能力，不影响既有团队/会话/文档/历史接口。
2. 旧账号无需迁移即可运行；未配置模型时默认行为为 Echo 基础对话。
