# 配置参考

Content Supply Platform 通过 YAML 配置文件 + 环境变量管理所有配置。

## 配置文件

| 文件 | 说明 |
|------|------|
| `configs/app.yaml` | 主配置（数据库/Redis/LLM/调度器/API） |
| `configs/feeds.yaml` | 初始 RSS 订阅源 |
| `configs/hot_sources.yaml` | 热搜平台配置 |
| `configs/cleanup_policies.yaml` | 清理策略配置 |

## 主配置 (app.yaml)

### MySQL 配置

```yaml
mysql:
  host: "localhost"
  port: 3306
  user: "root"
  password: ""
  database: "rec_platform"
  pool_size: 5
  max_overflow: 10
```

支持环境变量覆盖：`MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`。

### Redis 配置

```yaml
redis:
  host: "localhost"
  port: 6379
  password: ""
  db: 0
```

支持环境变量覆盖：`REDIS_HOST`、`REDIS_PORT`、`REDIS_PASSWORD`、`REDIS_DB`。

### LLM 配置

```yaml
llm:
  base_url: "http://localhost:11434/v1"
  api_key: "ollama"
  model: "qwen2.5:7b"
  max_tokens: 2048
  temperature: 0.7
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| base_url | LLM API 地址 | `http://localhost:11434/v1` |
| api_key | API Key | `ollama` |
| model | 模型名称 | `qwen2.5:7b` |
| max_tokens | 最大输出 token | `2048` |
| temperature | 生成温度 | `0.7` |

支持的 LLM 后端：

| 后端 | base_url | api_key |
|------|----------|---------|
| Ollama | `http://localhost:11434/v1` | `ollama` |
| vLLM | `http://localhost:8000/v1` | `empty` |
| OpenAI | `https://api.openai.com/v1` | `sk-xxx` |

### 调度器配置

```yaml
scheduler:
  enabled: true
  hot_track_interval: 3600
  cleanup_cron: "0 3 * * *"
  rewrite_cron: "0 4 * * *"
  auto_confirm_interval: 3600
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| enabled | 是否启用调度器 | `true` |
| hot_track_interval | 热搜采集间隔（秒） | `3600` |
| cleanup_cron | 清理扫描 cron | `0 3 * * *` |
| rewrite_cron | LLM 改写 cron | `0 4 * * *` |
| auto_confirm_interval | 自动确认检查间隔（秒） | `3600` |

### 通知配置

```yaml
notification:
  enabled: false
  webhook_url: ""
  channel: "webhook"
```

| channel 值 | 说明 |
|-------------|------|
| webhook | 通用 HTTP POST |
| wecom | 企业微信 |
| feishu | 飞书 |
| dingtalk | 钉钉 |

### 服务器配置

```yaml
server:
  host: "0.0.0.0"
  port: 8010
  workers: 1
```

## RSS 订阅源 (feeds.yaml)

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
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| name | 源名称 | - |
| url | Feed URL | - |
| source_type | 源类型 | `rss` |
| category | 分类 | - |
| poll_interval | 轮询间隔（秒） | `1800` |

## 热搜平台 (hot_sources.yaml)

```yaml
sources:
  - name: hackernews
    adapter: hackernews
    url: "https://news.ycombinator.com/"
    interval: 3600
    enabled: true
```

| 字段 | 说明 |
|------|------|
| name | 平台名称 |
| adapter | 适配器名称 |
| url | 平台 URL |
| interval | 采集间隔（秒） |
| enabled | 是否启用 |

## 清理策略 (cleanup_policies.yaml)

```yaml
policies:
  - source_type: rss
    ttl_days: 30
    max_items: 10000
    min_quality: 0.2

  - source_type: hot_keyword
    ttl_days: 7
    max_items: 5000
    min_quality: 0.3
    cold_start_ttl_days: 3

  - source_type: web
    ttl_days: 60
    max_items: 5000
    min_quality: 0.2

cleanup_schedule: "0 3 * * *"
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| source_type | 针对的数据源类型 | - |
| ttl_days | 过期天数 | `30` |
| max_items | 最大容量 | `10000` |
| min_quality | 最低质量分 | `0.2` |
| cold_start_ttl_days | 冷启动失败过期天数 | `3` |
| cleanup_schedule | Cron 表达式 | `0 3 * * *` |

## 环境变量

| 变量 | 说明 | 优先级 |
|------|------|--------|
| `DATABASE_URL` | 完整数据库 URL | 最高 |
| `DB_ENGINE` | 数据库引擎（mysql/sqlite） | 高 |
| `SQLITE_PATH` | SQLite 文件路径 | 中 |
| `MYSQL_HOST` | MySQL 主机 | 高 |
| `MYSQL_PORT` | MySQL 端口 | 高 |
| `MYSQL_USER` | MySQL 用户 | 高 |
| `MYSQL_PASSWORD` | MySQL 密码 | 高 |
| `MYSQL_DATABASE` | MySQL 数据库 | 高 |
| `REDIS_HOST` | Redis 主机 | 高 |
| `REDIS_PORT` | Redis 端口 | 高 |
| `LLM_BASE_URL` | LLM API 地址 | 高 |
| `LLM_API_KEY` | LLM API Key | 高 |
| `LLM_MODEL` | LLM 模型 | 高 |
