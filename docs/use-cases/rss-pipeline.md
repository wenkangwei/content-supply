# RSS 自动采集管道

本案例展示如何配置一个完整的 RSS 自动采集管道。

## 场景

你需要持续从多个技术博客和新闻网站采集内容，自动去重、评分后入库，供推荐系统消费。

## Step 1 — 配置 RSS 源

编辑 `configs/feeds.yaml`：

```yaml
feeds:
  - name: "Hacker News"
    url: "https://hnrss.org/frontpage"
    source_type: "rss"
    category: "tech"
    poll_interval: 1800

  - name: "TechCrunch"
    url: "https://techcrunch.com/feed/"
    source_type: "rss"
    category: "tech"
    poll_interval: 3600

  - name: "36Kr"
    url: "https://36kr.com/feed"
    source_type: "rss"
    category: "tech"
    poll_interval: 3600
```

## Step 2 — 启动服务

```bash
cd ~/workspace/ai_project/content-supply
python3.10 -m uvicorn content_supply.main:app --host 0.0.0.0 --port 8010
```

服务启动后，调度器会自动为每个 Feed 创建定时任务。

## Step 3 — 手动验证

```bash
# 手动触发第一个 Feed 的抓取
curl -X POST http://localhost:8010/crawl/feed/1

# 查看入库内容
curl "http://localhost:8010/items?source_type=rss&page_size=5"
```

## Step 4 — 查看自动调度效果

等待 `poll_interval` 时间后：

```bash
# 查看抓取任务状态
curl http://localhost:8010/tasks

# 查看内容数量
curl "http://localhost:8010/items?limit=1"
```

## 数据流

```
feeds.yaml → Feed 注册 → Scheduler 创建定时任务
    ↓ (每 poll_interval)
RSSCrawler.fetch(url) → feedparser 解析 → CrawledItem 列表
    ↓
ContentProcessor → 去重 + 标签 + 质量评分
    ↓
ItemWriter → MySQL cs_items + Redis item_pool:all
    ↓
推荐系统消费
```

## 监控

```bash
# Feed 状态
curl http://localhost:8010/feeds

# 健康检查
curl http://localhost:8010/api/health
```
