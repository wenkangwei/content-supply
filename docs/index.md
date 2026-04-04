# Content Supply Platform

**多源内容采集、LLM 改写与智能内容池管理平台**

---

![](https://img.shields.io/badge/Python-3.10+-blue)
![](https://img.shields.io/badge/FastAPI-0.115+-green)
![](https://img.shields.io/badge/License-MIT-yellow)

## 一句话介绍

Content Supply Platform 是一个独立的**内容供给中间件**，介于外部内容源和推荐系统之间。它负责：

1. **多源采集** — RSS 订阅、通用网页、国内外热搜词
2. **智能处理** — 去重、标签提取、质量评分、LLM 改写
3. **统一输出** — 写入共享 MySQL + Redis，供下游推荐系统消费

## 快速体验

=== "Step 1 — 启动服务"

    ```bash
    cd ~/workspace/ai_project/content-supply
    python3.10 -m uvicorn content_supply.main:app --host 0.0.0.0 --port 8010
    ```

=== "Step 2 — 添加 RSS 源"

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

=== "Step 3 — 抓取内容"

    ```bash
    # 触发 RSS 抓取
    curl -X POST http://localhost:8010/crawl/feed/1

    # 查看入库内容
    curl "http://localhost:8010/items?source_type=rss&page_size=5"
    ```

=== "Step 4 — 探索更多"

    ```bash
    # 搜索内容
    curl -X POST http://localhost:8010/items/search \
      -H "Content-Type: application/json" \
      -d '{"query": "AI", "page_size": 5}'

    # 采集热搜词
    curl -X POST http://localhost:8010/hot/trigger

    # 查看热搜词
    curl "http://localhost:8010/hot/keywords?limit=10"

    # 查看清理策略
    curl http://localhost:8010/cleanup/policies
    ```

## 核心能力一览

| 能力 | 说明 | 状态 |
|------|------|------|
| RSS 订阅抓取 | 定期轮询 RSS/Atom feed，自动解析入库 | ✅ |
| 通用网页抓取 | 任意 URL 正文/图片提取（trafilatura）+ 微信公众号文章 | ✅ |
| 热搜词采集 | HN / Reddit / Google 多平台适配器 | ✅ |
| 热点内容抓取 | 按热搜词搜索并抓取相关文章 | ✅ |
| LLM 内容改写 | paraphrase / summarize / expand 三种模式 | ✅ |
| 内容去重 | URL 精确匹配 + SHA256 内容哈希 | ✅ |
| 标签提取 | 中英文关键词自动提取 | ✅ |
| 质量评分 | 多维规则引擎（长度+图片+来源+标签） | ✅ |
| 内容池管理 | 单池多标签（source_type + category） | ✅ |
| 过期清理 | TTL + 容量 + 质量 + 冷启动失败（审核制） | ✅ |
| 审核通知 | Webhook / 企微 / 飞书 / 钉钉 | ✅ |
| 定时调度 | APScheduler 统一编排 | ✅ |
| 标签挖掘 | LLM 深度标签分析 | 🔲 占位 |

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| 数据库 | SQLAlchemy async + aiomysql（生产）/ aiosqlite（开发） |
| 缓存 | Redis |
| HTTP | httpx (async) |
| RSS | feedparser |
| 网页提取 | trafilatura |
| LLM | OpenAI-compatible API（Ollama / vLLM / OpenAI） |
| 调度 | APScheduler |
| CLI | Click |

## 项目仓库

```
content-supply/
├── content_supply/
│   ├── api/          # FastAPI 路由（31 个端点）
│   ├── models/       # ORM 模型（6 张表）
│   ├── schemas/      # Pydantic 请求/响应
│   ├── services/     # 业务逻辑（12 个服务）
│   ├── config.py     # 配置系统
│   ├── db.py         # 数据库管理
│   ├── main.py       # 应用入口
│   └── cli.py        # CLI 入口
├── configs/          # YAML 配置
├── tests/            # 测试（66 tests）
├── scripts/          # SQL DDL
└── docs/             # 本文档
```
