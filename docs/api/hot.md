# 热搜采集 API

管理热搜词的采集和查看。

## 触发热搜词采集

```
POST /hot/trigger
```

触发所有启用平台的热搜词采集。

### 响应示例

```json
{
  "status": "triggered",
  "keywords_collected": 55,
  "platforms": ["hackernews", "reddit", "google"],
  "message": "Hot keyword tracking triggered"
}
```

## 查看热搜词

```
GET /hot/keywords
```

### 查询参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| limit | int | 20 | 返回条数 |
| platform | string | - | 按平台筛选 |
| category | string | - | 按分类筛选 |

### 响应示例

```json
{
  "keywords": [
    {
      "id": 1,
      "keyword": "AI Agents",
      "platform": "hackernews",
      "rank": 1,
      "hot_score": 950.0,
      "category": "tech",
      "fetched_at": "2026-04-04T10:00:00",
      "content_fetched": false,
      "created_at": "2026-04-04T10:00:00"
    }
  ],
  "total": 55
}
```

## 支持的平台

| platform 值 | 说明 |
|--------------|------|
| hackernews | Hacker News |
| reddit | Reddit |
| google | Google Trends |
| baidu | 百度热搜 |
| weibo | 微博热搜 |
| zhihu | 知乎热榜 |
| douyin | 抖音热点 |
