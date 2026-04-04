# 安装部署

## 环境要求

| 依赖 | 最低版本 |
|------|----------|
| Python | 3.10+ |
| MySQL | 8.0+ (生产环境) |
| Redis | 7.0+ |
| pip | 23.0+ |

## 安装方式

### 方式一：从源码安装（推荐）

```bash
# 克隆项目
cd ~/workspace/ai_project
git clone <repo-url> content-supply
cd content-supply

# 创建虚拟环境
python3.10 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e ".[dev]"
```

### 方式二：pip 直接安装

```bash
pip install -e ~/workspace/ai_project/content-supply
```

## 配置

### 1. 数据库配置

项目默认使用 **SQLite** 进行本地开发，无需额外配置数据库。

生产环境需要 MySQL 8.0+，通过环境变量切换：

```bash
export DB_ENGINE=mysql
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=rec_platform
```

### 2. Redis 配置

本地开发可跳过 Redis（功能降级为仅写 MySQL）。

生产环境：

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
```

### 3. LLM 配置

支持任何 OpenAI-compatible API：

```bash
# 使用 Ollama（本地）
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_API_KEY=ollama
export LLM_MODEL=qwen2.5:7b

# 使用 vLLM
export LLM_BASE_URL=http://localhost:8000/v1
export LLM_API_KEY=empty
export LLM_MODEL=Qwen/Qwen2.5-7B-Instruct

# 使用 OpenAI
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_API_KEY=sk-xxx
export LLM_MODEL=gpt-4o-mini
```

### 4. 编辑配置文件

```bash
# 主配置
vim configs/app.yaml

# RSS 订阅源
vim configs/feeds.yaml

# 热搜平台
vim configs/hot_sources.yaml

# 清理策略
vim configs/cleanup_policies.yaml
```

## 启动服务

```bash
# 开发模式（SQLite，无需 MySQL/Redis）
python3.10 -m uvicorn content_supply.main:app --host 0.0.0.0 --port 8010 --reload

# 或使用 CLI
content-supply serve --host 0.0.0.0 --port 8010
```

启动成功后访问：

| 地址 | 说明 |
|------|------|
| http://localhost:8010/docs | Swagger UI |
| http://localhost:8010/redoc | ReDoc |
| http://localhost:8010/api/health | 健康检查 |

## 验证安装

```bash
# 健康检查
curl http://localhost:8010/api/health

# 添加 RSS 源
curl -X POST http://localhost:8010/feeds \
  -H "Content-Type: application/json" \
  -d '{"name": "HN", "url": "https://hnrss.org/frontpage", "source_type": "rss", "category": "tech"}'

# 触发抓取
curl -X POST http://localhost:8010/crawl/feed/1

# 查看内容
curl "http://localhost:8010/items?page_size=5"
```
