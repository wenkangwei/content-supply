# Feed 管理 API

管理 RSS/Atom 订阅源。

## 列出所有 Feed

```
GET /feeds
```

### 查询参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| skip | int | 0 | 跳过条数 |
| limit | int | 20 | 返回条数 |

### 响应示例

```json
[
  {
    "id": 1,
    "name": "Hacker News",
    "url": "https://hnrss.org/frontpage",
    "source_type": "rss",
    "category": "tech",
    "poll_interval": 1800,
    "status": "active",
    "last_fetched_at": "2026-04-04T10:00:00",
    "error_count": 0,
    "created_at": "2026-04-04T09:00:00"
  }
]
```

## 添加 Feed

```
POST /feeds
```

### 请求体

```json
{
  "name": "Hacker News",
  "url": "https://hnrss.org/frontpage",
  "source_type": "rss",
  "category": "tech",
  "poll_interval": 1800
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 源名称 |
| url | string | ✅ | Feed URL（唯一） |
| source_type | string | ✅ | rss / atom / web / hot_search |
| category | string | ❌ | 分类标签 |
| poll_interval | int | ❌ | 轮询间隔（秒），默认 1800 |

## 更新 Feed

```
PUT /feeds/{feed_id}
```

### 请求体

```json
{
  "name": "HN Frontpage",
  "poll_interval": 3600
}
```

## 删除 Feed

```
DELETE /feeds/{feed_id}
```

## 切换 Feed 状态

```
POST /feeds/{feed_id}/toggle
```

切换 Feed 的 `status`：`active` ↔ `paused`。

### 响应

```json
{
  "id": 1,
  "name": "Hacker News",
  "status": "paused",
  "message": "Feed toggled"
}
```
