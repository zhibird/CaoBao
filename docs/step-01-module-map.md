# 步骤 01 - 项目骨架模块地图

## 这一步为什么存在
这一步先搭建一个可以运行的后端骨架，还没有任何 AI 功能。

如果跳过这一步，后面每个功能都会变成零散的代码，很难调试。

## 模块职责

- `app/main.py`
  - 创建 FastAPI 应用。
  - 注册全局配置和路由。

- `app/core/config.py`
  - 集中管理环境变量。
  - 避免在路由/服务代码里写死常量。

- `app/api/routes/*.py`
  - 处理 HTTP 协议细节。
  - 把请求/响应处理和业务逻辑分开。

- `app/schemas/*.py`
  - 校验输入和输出。
  - 作为客户端和后端之间的"合同"。

- `app/services/*.py`
  - 存放可复用的业务逻辑。
  - 让路由处理函数保持精简，更容易测试。

- `tests/*.py`
  - 从用户角度验证 API 行为是否正确。
  - 防止后续加功能时意外破坏已有功能。

## 运行时调用流程

1. 客户端发送 `POST /api/v1/chat/echo`。
2. 路由把请求体解析成 `ChatEchoRequest`。
3. 路由调用 `ChatService.echo(...)`。
4. 服务返回 `ChatEchoResponse`。
5. FastAPI 把它序列化成 JSON 返回给客户端。
