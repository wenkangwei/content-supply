---
name: content-supply
description: >
  内容供给平台操作 skill。当用户需要管理内容源（RSS Feed / 网站源）、
  触发内容抓取（RSS / 单 URL / 网站列表页 / 即梦 AI）、查询搜索内容池、
  管理热搜词、触发 LLM 内容改写、管理内容过期清理、查看抓取任务状态时，
  使用此 skill。也适用于用户提到"抓取"、"爬取"、"采集"、"内容管理"、
  "RSS"、"feed"、"内容池"、"热搜"等关键词的场景。
  通过 HTTP API 调用本地 content-supply 服务（默认 http://localhost:8010）。
---

# Content Supply Platform — Agent 操作手册

内容供给平台 API 运行在 `http://localhost:8010`，所有端点返回 JSON。
使用 httpx / requests / curl 调用即可。

## 通用约定

- Content-Type: `application/json`
- 分页参数: `page` (从1开始), `page_size` (默认20)
- 错误响应: `{"detail": "error message"}`

---

## 1. Feed 管理

### 添加 RSS 源

```
POST /feeds
{"name": "Feed名称", "url": "https://example.com/feed", "source_type": "rss", "category": "tech", "poll_interval": 1800}
```

### 列出所有 Feed

```
GET /feeds?limit=100
```

### 更新 Feed

```
PUT /feeds/{id}
{"name": "新名称", "poll_interval": 3600}
```

### 删除 Feed

```
DELETE /feeds/{id}
```

### 暂停/恢复 Feed

```
POST /feeds/{id}/toggle
```

---

## 2. 网站源管理

### 列出所有配置的网站源

```
GET /crawl/web-sources
```

响应示例:
```json
{
  "sources": [
    {"name": "36Kr热门", "list_url": "https://36kr.com/hot-list/catalog", "list_css": "a.article-item-title", "category": "tech", "poll_interval": 1800, "max_articles": 10, "enabled": false}
  ],
  "total": 1
}
```

### 触发指定网站源抓取

```
POST /crawl/web-source/{source_name}
```

`source_name` 对应配置中的 `name` 字段（如 "36Kr热门"）。

---

## 3. 内容抓取

### 触发 RSS Feed 抓取

```
POST /crawl/feed/{feed_id}
```

### 抓取单个 URL

```
POST /crawl/url
{"url": "https://example.com/article", "category": "tech"}
```

支持类型: 通用网页、微信公众号文章 (`mp.weixin.qq.com/s/xxx`)、即梦详情页。

### 抓取即梦 AI 作品

```
POST /crawl/jimeng
```

批量抓取即梦 AI 创作广场作品，包含 prompt、图片、seed 等信息。

---

## 4. 内容查询

### 内容列表

```
GET /items?page_size=20&source_type=rss&category=tech&status=published
```

### 内容详情

```
GET /items/{item_id}
```

### 搜索内容

```
POST /items/search
{"query": "AI", "page_size": 20, "source_type": "rss"}
```

搜索范围: title + summary + content 模糊匹配。

---

## 5. 热搜词

### 触发热搜词采集

```
POST /hot/trigger
```

### 查看热搜词列表

```
GET /hot/keywords?limit=20&platform=hackernews
```

---

## 6. LLM 内容改写

### 改写单个内容

```
POST /rewrite/{item_id}
{"rewrite_type": "paraphrase"}
```

改写类型: `paraphrase` (伪原创) / `summarize` (摘要) / `expand` (扩展)。

### 批量改写

```
POST /rewrite/batch
{"limit": 20, "source_type": "rss", "rewrite_type": "paraphrase"}
```

---

## 7. 清理管理

### 查看清理策略

```
GET /cleanup/policies
```

### 触发清理扫描

```
POST /cleanup/trigger
```

扫描不会直接删除，只生成待审核清单。

### 查看待审核清单

```
GET /cleanup/pending
```

### 确认删除

```
POST /cleanup/{log_id}/confirm
{"reviewer": "agent"}
```

### 拒绝删除

```
POST /cleanup/{log_id}/reject
{"reviewer": "agent"}
```

### 查看清理日志

```
GET /cleanup/logs?limit=20
```

---

## 8. 抓取任务历史

```
GET /tasks?task_type=rss&status=done&limit=50
```

`task_type` 可选: `rss`, `web`, `manual`, `hot_keyword`。
`status` 可选: `pending`, `running`, `done`, `failed`。

---

## 去重机制

所有抓取路径都经过 `ItemWriter.write()`，自动基于 URL 精确匹配 + SHA256 内容哈希去重，无需手动处理。

## 典型工作流

1. 添加内容源 → `POST /feeds` 或配置 `web_sources.yaml`
2. 触发抓取 → `POST /crawl/feed/{id}` 或 `POST /crawl/web-source/{name}`
3. 查看入库内容 → `GET /items` 或 `POST /items/search`
4. 改写内容 → `POST /rewrite/{item_id}`
5. 定期清理 → `POST /cleanup/trigger` → 审核 → 确认/拒绝
