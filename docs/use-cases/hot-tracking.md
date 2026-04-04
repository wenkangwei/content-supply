# 热点追踪

本案例展示如何跟踪国内外热点话题并自动抓取相关内容。

## 场景

你需要实时追踪 Hacker News、Reddit 等平台的热门话题，并根据热搜词自动搜索和抓取相关文章。

## Step 1 — 配置热搜源

编辑 `configs/hot_sources.yaml`：

```yaml
sources:
  - name: hackernews
    adapter: hackernews
    url: "https://news.ycombinator.com/"
    interval: 3600
    enabled: true

  - name: reddit
    adapter: reddit
    url: "https://www.reddit.com/"
    interval: 1800
    enabled: true

  - name: google
    adapter: google
    url: "https://trends.google.com/"
    interval: 3600
    enabled: true
```

## Step 2 — 触发热搜词采集

```bash
curl -X POST http://localhost:8010/hot/trigger
```

系统会并发采集所有启用平台的热搜词。

## Step 3 — 查看热搜词

```bash
# 所有平台
curl "http://localhost:8010/hot/keywords?limit=20"

# 按 platform 筛选
curl "http://localhost:8010/hot/keywords?platform=hackernews&limit=10"
```

## Step 4 — 热点内容自动抓取

采集到热搜词后，系统会：

1. 按关键词在 DuckDuckGo 搜索相关文章 URL
2. 并发调用 WebScraper 抓取正文
3. 走标准处理管线（去重 → 标签 → 评分）入库

## 数据流

```
HotTracker → 多平台适配器并发采集
    ↓
cs_hot_keywords 表（热搜词快照）
    ↓
HotContentFetcher → DuckDuckGo 搜索 → URL 列表
    ↓
WebScraper → trafilatura 正文提取
    ↓
ContentProcessor → 去重 + 标签 + 评分
    ↓
ItemWriter → MySQL + Redis
```

## 定时采集

在 `configs/app.yaml` 中配置：

```yaml
scheduler:
  hot_track_interval: 3600  # 每小时采集一次
```

调度器启动后会自动按间隔触发热搜词采集。
