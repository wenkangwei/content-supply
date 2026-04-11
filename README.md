# Content Supply Platform

**多源内容采集、LLM 改写与智能内容池管理平台**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](https://opensource.org/licenses/MIT)

---

## 一句话介绍

Content Supply Platform 是一个独立的**内容供给中间件**，介于外部内容源和推荐系统之间：

```
外部内容源 → Content Supply Platform → MySQL + Redis → 推荐系统
(RSS/网页/热搜)   (采集/处理/改写/管理)
```

## 核心能力

| 能力 | 说明 |
|------|------|
| RSS 订阅抓取 | 定期轮询 RSS/Atom feed，自动解析入库 |
| **网站源自动抓取** | **只需粘贴列表页 URL，自动发现最新文章并批量抓取（无需 CSS 选择器）** |
| 通用网页抓取 | 任意 URL 正文/图片提取（trafilatura） |
| 微信公众号抓取 | `mp.weixin.qq.com/s/` 文章专用提取器 |
| 即梦 AI 作品抓取 | 一键抓取即梦 AI 创作广场作品（prompt/图片/作者/seed） |
| 热搜词采集 | HackerNews / Reddit / Google 多平台适配器 |
| **热搜词→文章抓取** | **按热搜词自动搜索并抓取相关文章入库（DuckDuckGo + WebScraper）** |
| LLM 内容改写 | paraphrase / summarize / expand 三种模式 |
| 内容去重 | URL 精确匹配 + SHA256 内容哈希 |
| 标签提取 | 中英文关键词自动提取 |
| 质量评分 | 多维规则引擎（长度+图片+来源+标签） |
| 过期清理 | TTL + 容量 + 质量 + 冷启动失败（审核制） |
| 审核通知 | Webhook / 企微 / 飞书 / 钉钉 |
| 定时调度 | APScheduler 统一编排 |
| **Agent Skill** | **标准 Anthropic skill 格式，供 Agent 接入所有 CRUD 操作** |
| **CLI 快捷命令** | **`cs` shell 脚本 + `supply` Click CLI，无需手写 curl** |

## 快速开始

### 1. 启动服务

```bash
# SQLite 模式（开发，零依赖）
cd content-supply
python3.10 -m uvicorn content_supply.main:app --host 0.0.0.0 --port 8010

# MySQL 模式（生产，需先启动 Docker MySQL）
DB_ENGINE=mysql python3.10 -m uvicorn content_supply.main:app --host 0.0.0.0 --port 8010
```

> 默认使用 SQLite，无需 MySQL/Redis。生产环境使用 MySQL 需设置 `DB_ENGINE=mysql` 环境变量，数据库表自动创建。

### 2. Docker MySQL（推荐）

```bash
# 启动共享服务栈（MySQL + Redis + ClickHouse）
cd ../llm-rec-platform/docker
docker compose up -d mysql redis clickhouse

# MySQL 连接信息
# Host: localhost:3306
# Database: rec_platform
# User: rec_user / Password: rec_pass
```

### 3. 添加 RSS 源

```bash
# 方式一：cs 快捷脚本
./scripts/cs feeds add "Hacker News" "https://hnrss.org/frontpage" "tech"

# 方式二：完整 CLI
supply feed add "Hacker News" "https://hnrss.org/frontpage" --category tech

# 方式三：curl
curl -X POST http://localhost:8010/feeds \
  -H "Content-Type: application/json" \
  -d '{"name": "Hacker News", "url": "https://hnrss.org/frontpage", "source_type": "rss", "category": "tech"}'
```

### 4. 配置网站源（自动发现文章，无需 CSS 选择器）

编辑 `configs/web_sources.yaml`，粘贴列表页 URL 即可：

```yaml
web_sources:
  - name: "量子位"
    url: "https://www.qbitai.com/"      # 粘贴浏览器地址
    category: "ai"
    poll_interval: 1800
    max_articles: 10
    enabled: true
```

系统自动识别文章链接（基于 URL 路径、日期模式、文本长度等启发式规则），无需填写 CSS 选择器。

### 5. 抓取内容

```bash
# RSS 抓取
./scripts/cs crawl feed 1

# 任意网页
./scripts/cs crawl url "https://example.com/article"

# 微信公众号文章
./scripts/cs crawl url "https://mp.weixin.qq.com/s/xxxxxxxxxxxx"

# 即梦 AI 作品
./scripts/cs crawl jimeng

# 网站源抓取（自动发现）
./scripts/cs crawl web-source          # 列出所有网站源
./scripts/cs crawl web-source "量子位"  # 触发抓取
```

### 6. 热搜词 → 相关文章

```bash
# 采集热搜词（HN/Reddit/Google）
./scripts/cs hot trigger

# 查看热搜词
./scripts/cs hot keywords

# 自动搜索并抓取相关文章
./scripts/cs hot fetch              # 批量处理未抓取的热搜词
./scripts/cs hot fetch 42           # 抓取指定热搜词的相关文章
```

### 7. 查看与管理

```bash
# 内容查询
./scripts/cs items 5                       # 最新 5 条
./scripts/cs items search "Linux"          # 搜索
supply items get <item_id>                  # 详情

# 清理策略
./scripts/cs cleanup policies               # 查看策略
./scripts/cs cleanup trigger                # 触发扫描

# 抓取任务历史
./scripts/cs tasks
./scripts/cs tasks done                     # 按状态筛选
```

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| 数据库 | SQLAlchemy async + aiomysql（生产）/ aiosqlite（开发） — `DB_ENGINE=mysql` 切换 |
| 缓存 | Redis |
| HTTP | httpx (async) |
| RSS | feedparser |
| 网页提取 | trafilatura |
| 即梦 AI | 内嵌 SSR 数据解析 + 图片验证 |
| LLM | OpenAI-compatible API（Ollama / vLLM / OpenAI） |
| 调度 | APScheduler |
| CLI | Click |
| 文档 | MkDocs Material |

## 项目结构

```
content-supply/
├── content_supply/           # 主包
│   ├── api/                  # FastAPI 路由
│   │   ├── crawl.py          #   抓取: POST /crawl/url, /crawl/feed/{id}, /crawl/jimeng, /crawl/web-source/{name}
│   │   ├── feeds.py          #   Feed CRUD: GET/POST/PUT/DELETE /feeds, POST /feeds/{id}/toggle
│   │   ├── items.py          #   内容: GET /items, GET /items/{id}, POST /items/search
│   │   ├── hot.py            #   热搜: GET /hot/keywords, POST /hot/trigger
│   │   ├── rewrite.py        #   改写: POST /rewrite/{id}, POST /rewrite/batch
│   │   ├── cleanup.py        #   清理: GET /cleanup/policies, POST /cleanup/trigger, /confirm, /reject
│   │   ├── tags.py           #   标签: GET /tags, POST /tags/mine
│   │   ├── health.py         #   健康检查: GET /api/health
│   │   └── deps.py           #   依赖注入 (get_db session)
│   ├── models/               # SQLAlchemy ORM 模型
│   │   ├── base.py           #   Base = DeclarativeBase
│   │   ├── feed.py           #   cs_feeds 表 (RSS/Atom 订阅源)
│   │   ├── item.py           #   cs_items 表 (内容池核心表, URL+content_hash unique 去重)
│   │   ├── crawl_task.py     #   cs_crawl_tasks 表 (抓取任务追踪)
│   │   ├── rewrite_task.py   #   cs_rewrite_tasks 表 (LLM 改写任务)
│   │   ├── hot_keyword.py    #   cs_hot_keywords 表 (热搜词)
│   │   └── cleanup_log.py    #   cs_cleanup_logs 表 (清理日志)
│   ├── schemas/              # Pydantic v2 请求/响应
│   │   ├── feed.py           #   FeedCreate / FeedUpdate / FeedResponse
│   │   ├── item.py           #   ItemResponse / ItemSearchRequest
│   │   ├── task.py           #   CrawlUrlRequest / CrawlTaskResponse / JimengArtwork
│   │   └── cleanup.py        #   CleanupConfirmRequest
│   ├── services/             # 业务逻辑层
│   │   ├── types.py          #   共享数据类 CrawledItem
│   │   ├── rss_crawler.py    #   RSS/Atom 解析 (feedparser)
│   │   ├── web_scraper.py    #   通用网页提取 (trafilatura + 微信/即梦专用适配)
│   │   ├── web_source_crawler.py  # [NEW] 网站列表页文章发现+批量抓取 (BS4 CSS选择器)
│   │   ├── hot_tracker.py    #   多平台热搜词采集 (HN/Reddit/Google)
│   │   ├── hot_content_fetcher.py # 按热搜词搜索+抓取相关文章
│   │   ├── content_processor.py   # 去重哈希 + 标签提取 + 质量评分
│   │   ├── content_rewriter.py    # LLM 改写 (paraphrase/summarize/expand)
│   │   ├── item_writer.py    #   入库 + Redis 推送 (item_pool/hot_items/item_feat)
│   │   ├── feed_manager.py   #   Feed 数据库 CRUD 操作
│   │   ├── cleanup_manager.py     # 过期清理 (TTL/容量/质量策略)
│   │   ├── notification.py   #   审核通知 (Webhook/企微/飞书/钉钉)
│   │   ├── tag_miner.py      #   标签挖掘 (LLM 分析)
│   │   └── scheduler.py      #   APScheduler 编排 (RSS/热搜/清理/改写/网站源)
│   ├── config.py             # Pydantic Settings 配置加载 (支持 ${env:VAR:default})
│   ├── db.py                 # SQLAlchemy async engine + session (MySQL/SQLite 切换)
│   ├── main.py               # FastAPI app + lifespan (启动时建表)
│   └── cli.py                # Click CLI (serve/health/feed/crawl/items/hot/rewrite/cleanup/tasks)
│
├── configs/                  # YAML 配置文件
│   ├── app.yaml              #   全局配置 (MySQL/Redis/LLM/Scheduler/Notification)
│   ├── feeds.yaml            #   RSS 源列表 (name/url/poll_interval/category)
│   ├── web_sources.yaml      # [NEW] 网站源列表 (name/list_url/list_css/base_url/poll_interval)
│   ├── hot_sources.yaml      #   热搜平台配置
│   └── cleanup_policies.yaml #   清理策略 (TTL/容量/质量阈值)
│
├── skills/                   # [NEW] Agent Skill
│   └── content-supply/
│       └── SKILL.md          #   Anthropic 标准格式 skill，供 Agent 接入所有 API 操作
│
├── scripts/                  # 工具脚本
│   ├── init_tables.sql       #   MySQL DDL (cs_* 表)
│   ├── sync_to_rec.py        #   同步内容到推荐系统 Redis
│   └── cs                    # [NEW] Shell 快捷命令 (cs crawl url / cs items list / ...)
│
├── tests/                    # pytest 测试
│   ├── conftest.py           #   异步 SQLite 内存库 fixture
│   ├── test_rss_crawler.py   #   RSS 解析测试
│   ├── test_web_scraper.py   #   网页抓取测试
│   ├── test_hot_tracker.py   #   热搜采集测试
│   ├── test_content_processor.py  # 内容处理测试
│   └── test_integration.py   #   端到端集成测试
│
├── docs/                     # MkDocs 文档
│   ├── api/                  #   API 参考文档 (crawl/feeds/items/hot/rewrite/cleanup/tags)
│   ├── modules/              #   模块详解 (rss-crawler/web-scraper/scheduler/...)
│   ├── overview/             #   产品概述 (architecture/capabilities/background)
│   ├── use-cases/            #   使用案例 (rss-pipeline/hot-tracking/content-rewriting)
│   └── getting-started/      #   快速开始 (installation/quickstart)
│
├── pyproject.toml            # 项目配置 + 依赖 + Click CLI 入口点
├── mkdocs.yml                # 文档站点配置
├── feature_list.json         # 功能清单 (32 功能点)
└── claude-progress.txt       # 开发进度追踪
```

## 文档

本地启动文档站点：

```bash
mkdocs serve --dev-addr 0.0.0.0:8000
```

访问 http://localhost:8000 浏览完整文档，包括：

- [产品架构](docs/overview/architecture.md)
- [功能模块详解](docs/modules/rss-crawler.md)
- [API 参考](docs/api/overview.md)
- [使用案例](docs/use-cases/rss-pipeline.md)
- [路线图](docs/roadmap.md)

## API 端点一览

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/feeds` | GET/POST | Feed 列表/添加 |
| `/feeds/{id}` | PUT/DELETE | 更新/删除 |
| `/feeds/{id}/toggle` | POST | 暂停/恢复 |
| `/crawl/feed/{id}` | POST | 触发 Feed 抓取 |
| `/crawl/url` | POST | 抓取单个 URL |
| `/crawl/jimeng` | POST | 批量抓取即梦 AI 作品 |
| `/crawl/web-sources` | GET | 列出网站源配置 |
| `/crawl/web-source/{name}` | POST | 触发网站源抓取 |
| `/items` | GET | 内容列表 |
| `/items/{id}` | GET | 内容详情 |
| `/items/search` | POST | 搜索内容 |
| `/hot/keywords` | GET | 热搜词列表 |
| `/hot/trigger` | POST | 触发热搜采集 |
| `/rewrite/{id}` | POST | 触发改写 |
| `/rewrite/batch` | POST | 批量改写 |
| `/cleanup/policies` | GET | 清理策略 |
| `/cleanup/trigger` | POST | 触发清理扫描 |
| `/cleanup/pending` | GET | 待审核清单 |
| `/cleanup/{id}/confirm` | POST | 确认删除 |
| `/cleanup/{id}/reject` | POST | 拒绝删除 |
| `/cleanup/logs` | GET | 清理日志 |
| `/tasks` | GET | 抓取任务历史 |

完整 API 文档启动后访问 http://localhost:8010/docs（Swagger UI）。

## 与推荐系统联调

Content Supply Platform 通过共享 **MySQL + Redis** 与推荐系统（[llm-rec-platform](../llm-rec-platform/)）对接：

```
Content Supply (8010)                    LLM Rec Platform (8001)
───────────────                         ─────────────────
crawl/jimeng ─┐
crawl/url ────┤─→ MySQL (cs_items) ─→ sync_to_rec.py ─→ Redis ─→ Recall
crawl/feed ──┘                                              │
                                                item_pool:all (SET)
                                                hot_items:global (ZSET)
                                                item_feat:{id} (HASH)
                                                item_sim:{id} (JSON)
                                                community_hot:* (ZSET)
```

### 同步命令

```bash
# 同步全部内容到推荐系统 Redis（自动从 MySQL 读取，回退 SQLite）
python3.10 scripts/sync_to_rec.py

# 清理后全量同步
python3.10 scripts/sync_to_rec.py --clean

# 只同步指定来源
python3.10 scripts/sync_to_rec.py --source jimeng
```

### 联调验证

```bash
# 1. 启动 Docker 服务栈
cd ../llm-rec-platform/docker && docker compose up -d mysql redis

# 2. 启动 content-supply（MySQL 模式）
DB_ENGINE=mysql python3.10 -m uvicorn content_supply.main:app --port 8010

# 3. 抓取内容
curl -X POST http://localhost:8010/crawl/jimeng

# 4. 同步到 Redis
python3.10 scripts/sync_to_rec.py --clean

# 5. 推荐系统获取推荐
curl -X POST http://localhost:8001/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_001", "scene": "home", "num": 10}'

# 6. 通过推荐系统 Agent 查询内容池
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "admin", "message": "数据库里有多少内容"}'
# → 内容池共有 36 条内容，分布如下：rss: 20 条, jimeng: 15 条, manual: 1 条
```

## 路线图

| 版本 | 主题 | 核心内容 |
|------|------|----------|
| v1.0 | 当前版本 | 32 功能点，66 测试通过，即梦 AI 抓取，MySQL 生产模式 |
| v1.1 | 安全加固 | API 认证、输入校验、速率限制、Alembic |
| v1.2 | 性能优化 | 批量写入、jieba 中文分词、国内热搜适配器 |
| v1.3 | Playwright | 浏览器抓取、JS 渲染、agent 模拟 |

详见 [路线图](docs/roadmap.md)。

## License

MIT
