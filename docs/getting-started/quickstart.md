# 五分钟体验

本指南将帮助你在 **5 分钟内** 跑通 Content Supply Platform 的核心流程。

!!! tip "前提条件"
    - Python 3.10+ 已安装
    - 无需 MySQL / Redis（默认使用 SQLite）

## Step 1 — 启动服务

```bash
cd ~/workspace/ai_project/content-supply
python3.10 -m uvicorn content_supply.main:app --host 0.0.0.0 --port 8010
```

看到 `Uvicorn running on http://0.0.0.0:8010` 即启动成功。

## Step 2 — 添加 RSS 源

```bash
curl -X POST http://localhost:8010/feeds \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hacker News",
    "url": "https://hnrss.org/frontpage",
    "source_type": "rss",
    "category": "tech",
    "poll_interval": 1800
  }'
```

## Step 3 — 抓取内容

```bash
# 触发 RSS 抓取
curl -X POST http://localhost:8010/crawl/feed/1

# 查看入库内容
curl "http://localhost:8010/items?source_type=rss&page_size=5"
```

你将看到类似输出：

```json
{
  "items": [
    {
      "id": "abc123",
      "title": "Show HN: A new approach to...",
      "url": "https://news.ycombinator.com/...",
      "source_type": "rss",
      "quality_score": 0.65,
      "tags": "tech, programming"
    }
  ],
  "total": 20,
  "page": 1
}
```

## Step 4 — 采集热搜词

```bash
# 触发热搜词采集（HN + Reddit + Google）
curl -X POST http://localhost:8010/hot/trigger

# 查看热搜词
curl "http://localhost:8010/hot/keywords?limit=10"
```

## Step 5 — 搜索内容

```bash
curl -X POST http://localhost:8010/items/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI", "page_size": 5}'
```

## 下一步

- [产品架构](../overview/architecture.md) — 了解整体设计
- [配置参考](../configuration.md) — 自定义配置
- [API 参考](../api/overview.md) — 完整 API 文档
- [使用案例](../use-cases/rss-pipeline.md) — 实战场景
