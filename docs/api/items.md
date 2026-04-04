# 内容查询 API

查询内容池中的内容。

## 内容列表

```
GET /items
```

### 查询参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| skip | int | 0 | 跳过条数 |
| limit | int | 20 | 返回条数 |
| source_type | string | - | 按来源类型筛选 |
| category | string | - | 按分类筛选 |
| status | string | published | 按状态筛选 |

### 响应示例

```json
{
  "items": [
    {
      "id": "a1b2c3",
      "title": "Show HN: A new approach to...",
      "summary": "Summary text...",
      "url": "https://news.ycombinator.com/...",
      "source_type": "rss",
      "category": "tech",
      "tags": "programming, open-source",
      "quality_score": 0.72,
      "is_rewritten": false,
      "status": "published",
      "published_at": "2026-04-04T08:00:00",
      "created_at": "2026-04-04T09:00:00"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

## 内容详情

```
GET /items/{item_id}
```

### 响应示例

```json
{
  "id": "a1b2c3",
  "title": "Show HN: A new approach to...",
  "summary": "Summary text...",
  "content": "Full article content...",
  "original_content": null,
  "url": "https://news.ycombinator.com/...",
  "image_url": "https://...",
  "author": "John Doe",
  "source_name": "Hacker News",
  "source_type": "rss",
  "category": "tech",
  "tags": "programming, open-source",
  "quality_score": 0.72,
  "content_hash": "sha256hash...",
  "is_rewritten": false,
  "exposure_count": 0,
  "click_count": 0,
  "status": "published",
  "published_at": "2026-04-04T08:00:00",
  "created_at": "2026-04-04T09:00:00",
  "updated_at": "2026-04-04T09:00:00"
}
```

## 搜索内容

```
POST /items/search
```

### 请求体

```json
{
  "query": "AI",
  "page_size": 20,
  "page": 1,
  "source_type": "rss",
  "category": "tech"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | ✅ | 搜索关键词 |
| page_size | int | ❌ | 每页条数，默认 20 |
| page | int | ❌ | 页码，默认 1 |
| source_type | string | ❌ | 按来源筛选 |
| category | string | ❌ | 按分类筛选 |

搜索范围：`title` + `summary` + `content`（模糊匹配）。
