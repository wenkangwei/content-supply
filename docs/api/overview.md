# API 概述

Content Supply Platform 提供 RESTful API，共 **31 个端点**。

## 基本信息

| 项目 | 说明 |
|------|------|
| Base URL | `http://localhost:8010` |
| 协议 | HTTP/1.1 |
| 数据格式 | JSON |
| 认证 | 暂无（本地部署） |
| 文档 | `/docs`（Swagger UI）/ `/redoc`（ReDoc） |

## 模块划分

| 模块 | 前缀 | 说明 |
|------|------|------|
| Health | `/api/health` | 健康检查 |
| Feeds | `/feeds` | Feed CRUD |
| Items | `/items` | 内容查询 |
| Crawl | `/crawl` | 抓取触发 |
| Hot | `/hot` | 热搜采集 |
| Rewrite | `/rewrite` | 内容改写 |
| Cleanup | `/cleanup` | 清理管理 |
| Tags | `/tags` | 标签挖掘 |

## 通用响应格式

### 成功响应

```json
{
  "data": { ... },
  "message": "success"
}
```

### 分页响应

```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### 错误响应

```json
{
  "detail": "Error message"
}
```

## HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 202 | 已接受（异步任务） |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
