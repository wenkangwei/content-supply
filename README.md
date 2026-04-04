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
| 通用网页抓取 | 任意 URL 正文/图片提取（trafilatura） |
| 微信公众号抓取 | `mp.weixin.qq.com/s/` 文章专用提取器 |
| 热搜词采集 | HackerNews / Reddit / Google 多平台适配器 |
| 热点内容抓取 | 按热搜词搜索并抓取相关文章 |
| LLM 内容改写 | paraphrase / summarize / expand 三种模式 |
| 内容去重 | URL 精确匹配 + SHA256 内容哈希 |
| 标签提取 | 中英文关键词自动提取 |
| 质量评分 | 多维规则引擎（长度+图片+来源+标签） |
| 过期清理 | TTL + 容量 + 质量 + 冷启动失败（审核制） |
| 审核通知 | Webhook / 企微 / 飞书 / 钉钉 |
| 定时调度 | APScheduler 统一编排 |

## 快速开始

### 1. 启动服务

```bash
cd content-supply
python3.10 -m uvicorn content_supply.main:app --host 0.0.0.0 --port 8010
```

> 默认使用 SQLite，无需 MySQL/Redis。生产环境切换见 [配置参考](docs/configuration.md)。

### 2. 添加 RSS 源

```bash
curl -X POST http://localhost:8010/feeds \
  -H "Content-Type: application/json" \
  -d '{"name": "Hacker News", "url": "https://hnrss.org/frontpage", "source_type": "rss", "category": "tech"}'
```

### 3. 抓取内容

```bash
# RSS 抓取
curl -X POST http://localhost:8010/crawl/feed/1

# 任意网页
curl -X POST http://localhost:8010/crawl/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# 微信公众号文章
curl -X POST http://localhost:8010/crawl/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://mp.weixin.qq.com/s/xxxxxxxxxxxx"}'
```

### 4. 查看与管理

```bash
# 查看内容
curl http://localhost:8010/items?page_size=5

# 搜索
curl -X POST http://localhost:8010/items/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI", "page_size": 5}'

# 热搜词采集
curl -X POST http://localhost:8010/hot/trigger

# 清理策略
curl http://localhost:8010/cleanup/policies
```

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
| 文档 | MkDocs Material |

## 项目结构

```
content-supply/
├── content_supply/
│   ├── api/              # FastAPI 路由（31 个端点）
│   ├── models/           # ORM 模型（6 张表）
│   ├── schemas/          # Pydantic 请求/响应
│   ├── services/         # 业务逻辑（12 个服务）
│   ├── config.py         # 配置系统
│   ├── db.py             # 数据库管理
│   ├── main.py           # 应用入口
│   └── cli.py            # CLI 入口
├── configs/              # YAML 配置
├── tests/                # 测试（66 tests）
├── scripts/              # SQL DDL
└── docs/                 # 产品文档（MkDocs）
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

完整 API 文档启动后访问 http://localhost:8010/docs（Swagger UI）。

## 路线图

| 版本 | 主题 | 核心内容 |
|------|------|----------|
| v1.0 | 当前版本 | 32 功能点，66 测试通过 |
| v1.1 | 安全加固 | API 认证、输入校验、速率限制、Alembic |
| v1.2 | 性能优化 | 批量写入、jieba 中文分词、国内热搜适配器 |
| v1.3 | Playwright | 浏览器抓取、JS 渲染、agent 模拟 |

详见 [路线图](docs/roadmap.md)。

## License

MIT
