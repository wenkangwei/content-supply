# Content Supply Platform — 开发规范

## 项目概述

内容供给平台，为 LLM 推荐系统提供多源内容采集、处理和管理。独立于 `llm-rec-platform` 项目，通过共享 MySQL `rec_platform` 数据库对接。

## 核心能力

1. **RSS 订阅抓取** — 定期轮询 RSS/Atom feed
2. **通用网页抓取** — trafilatura 提取正文/图片
3. **热点热搜词抓取** — 国内外多平台热搜词采集 + 关联内容抓取
4. **LLM 内容改写** — 伪原创/摘要/扩展
5. **内容池管理** — 单池多标签（source_type + category）
6. **过期内容清理** — TTL + 容量淘汰 + 质量淘汰（审核制）
7. **优质标签挖掘** — LLM 定期分析入库内容标签（先占接口）

## 技术栈

- Python 3.11+ / FastAPI / SQLAlchemy async / APScheduler
- httpx / feedparser / trafilatura / OpenAI-compatible LLM
- MySQL (aiomysql) / Redis

## 代码规范

- 使用 SQLAlchemy 2.0 async ORM（Mapped 类型注解）
- Pydantic v2 用于请求/响应 schema 和配置
- 异步优先：所有 IO 操作用 async/await
- 服务层与 API 层分离：services/ 放业务逻辑，api/ 只做路由
- 配置集中在 configs/ 目录，YAML 格式
- 支持 `${env:VAR:default}` 环境变量替换

## 项目结构

```
content_supply/
├── config.py        # Pydantic Settings 配置加载
├── db.py            # SQLAlchemy async engine + session
├── main.py          # FastAPI app + lifespan
├── models/          # ORM 模型（cs_feeds, cs_items, cs_crawl_tasks, cs_hot_keywords, cs_rewrite_tasks, cs_cleanup_logs）
├── schemas/         # Pydantic 请求/响应
├── services/        # 业务逻辑
├── api/             # FastAPI 路由
└── cli.py           # Click CLI
```

## 数据库

- 共享 llm-rec-platform 的 MySQL `rec_platform` 数据库
- 表名前缀 `cs_` 避免冲突
- DDL 脚本: `scripts/init_tables.sql`
- 开发环境可用 `await create_tables()` 自动建表

## 开发工作流

采用 agent-harness long-running 模式:
1. 每个会话读取 `claude-progress.txt` 了解上下文
2. 从 `feature_list.json` 选取最高优先级未通过功能
3. 实现 + 测试该功能
4. 标记 passes: true，git commit
5. 更新 `claude-progress.txt`

## 测试

- pytest + pytest-asyncio
- 测试用 SQLite 内存库，不依赖外部 MySQL
- `pytest tests/` 运行所有测试

## 关键约束

- 不导入 llm-rec-platform 的任何代码
- 与推荐系统仅通过 MySQL + Redis 对接
- 删除操作必须经过审核确认
- 所有 IO 操作异步
