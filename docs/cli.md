# CLI 手册

Content Supply Platform 提供命令行工具 `content-supply`（或 `python -m content_supply.cli`）。

## 安装

```bash
pip install -e ~/workspace/ai_project/content-supply
```

## 全局选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--base-url` | API 服务地址 | `http://localhost:8010` |

## 命令列表

### serve — 启动服务

```bash
content-supply serve --host 0.0.0.0 --port 8010
```

### health — 健康检查

```bash
content-supply health
```

### feed — Feed 管理

```bash
# 添加 RSS 源
content-supply feed add --name "HN" --url "https://hnrss.org/frontpage" --type rss --category tech

# 列出所有 Feed
content-supply feed list

# 删除 Feed
content-supply feed remove --id 1

# 暂停/恢复
content-supply feed toggle --id 1
```

### crawl — 触发抓取

```bash
# 抓取指定 Feed
content-supply crawl now --feed-id 1

# 抓取指定 URL
content-supply crawl url "https://example.com/article"
```

### items — 内容管理

```bash
# 列出内容
content-supply items list --source-type rss --limit 10

# 搜索内容
content-supply items search "AI" --limit 5
```

### hot — 热搜管理

```bash
# 触发热搜词采集
content-supply hot trigger

# 查看热搜词
content-supply hot keywords --limit 10 --platform hackernews
```

### rewrite — 内容改写

```bash
# 改写单个内容
content-supply rewrite single {item_id} --type paraphrase

# 批量改写
content-supply rewrite batch --source-type rss --type summarize --limit 10
```

### cleanup — 清理管理

```bash
# 查看清理策略
content-supply cleanup policies

# 触发清理扫描
content-supply cleanup trigger

# 查看待审核清单
content-supply cleanup pending

# 确认删除
content-supply cleanup confirm --log-id 1

# 拒绝删除
content-supply cleanup reject --log-id 1

# 查看清理日志
content-supply cleanup logs
```
