# 内容抓取 API

手动触发内容抓取任务。

## 抓取 Feed

```
POST /crawl/feed/{feed_id}
```

触发指定 Feed 的 RSS 抓取。

### 响应示例

```json
{
  "id": 1,
  "feed_id": 1,
  "url": "https://hnrss.org/frontpage",
  "task_type": "rss",
  "status": "done",
  "items_found": 20,
  "items_new": 15,
  "error_message": null
}
```

## 抓取 URL

```
POST /crawl/url
```

手动抓取指定 URL 的内容，支持通用网页和微信公众号文章。

### 请求体

```json
{
  "url": "https://example.com/article",
  "category": "tech"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | string | ✅ | 目标 URL |
| category | string | ❌ | 分类标签 |

### 成功响应

```json
{
  "task": {
    "id": 12,
    "url": "https://mp.weixin.qq.com/s/xxx",
    "task_type": "manual",
    "status": "done",
    "items_found": 1,
    "items_new": 1,
    "error_message": null,
    "finished_at": "2026-04-05T02:00:00"
  },
  "item": {
    "title": "文章标题",
    "url": "https://mp.weixin.qq.com/s/xxx",
    "content": "正文内容...",
    "author": "作者名",
    "image_url": "https://...",
    "published_at": "2026-04-04T21:03:03",
    "source_type": "manual",
    "tags": []
  }
}
```

### 错误响应（不支持的 URL）

```json
{
  "task": {
    "id": 13,
    "url": "https://mp.weixin.qq.com/cgi-bin/announce?...",
    "task_type": "manual",
    "status": "failed",
    "error_message": "不支持抓取: 微信公众号后台页面，请使用文章链接格式：mp.weixin.qq.com/s/xxx"
  },
  "item": null
}
```

### 支持的 URL 类型

| 类型 | 示例 | 说明 |
|------|------|------|
| 通用网页 | `https://example.com/article` | trafilatura 自动提取正文 |
| 微信公众号文章 | `https://mp.weixin.qq.com/s/xxx` | 专用提取器，支持正文/标题/日期 |
| 同花顺等财经网站 | `https://stock.10jqka.com.cn/...` | 自动跳过 robots.txt（手动触发） |

### 不支持的 URL

| 类型 | 原因 |
|------|------|
| `mp.weixin.qq.com/cgi-bin/*` | 微信后台页面，需登录+JS渲染 |
| 登录/认证页面 | 需要登录态 |
| PDF/视频/音频文件 | 非 HTML 内容 |
