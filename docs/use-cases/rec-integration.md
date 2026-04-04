# 与推荐系统对接

本案例展示 Content Supply Platform 如何与下游推荐系统集成。

## 架构

```
Content Supply Platform → 共享存储 → 推荐系统
                           ↓
    ┌──────────────────────────────────┐
    │  MySQL (rec_platform)            │
    │  ├── cs_items（内容池）           │
    │  ├── cs_feeds                    │
    │  ├── cs_hot_keywords             │
    │  └── ...                         │
    │                                  │
    │  Redis                           │
    │  ├── item_pool:all (SET)         │
    │  └── hot_items:global (ZSET)     │
    └──────────────────────────────────┘
```

## 共享存储

### MySQL

两个系统共享 `rec_platform` 数据库：

- Content Supply 写入 `cs_items` 表
- 推荐系统读取 `cs_items` 表
- 表名以 `cs_` 前缀区分，避免冲突

### Redis

| Key | 类型 | 写入方 | 读取方 |
|-----|------|--------|--------|
| `item_pool:all` | SET | Content Supply | 推荐系统 |
| `hot_items:global` | ZSET | Content Supply | 推荐系统 |

## 推荐系统读取方式

### 方式 1：从 Redis 召回 ID

```python
import redis.asyncio as aioredis

redis = aioredis.from_url("redis://localhost:6379/0")

# 获取所有可推荐内容 ID
item_ids = await redis.smembers("item_pool:all")

# 获取热门内容 Top 50（按质量分排序）
hot_ids = await redis.zrevrange("hot_items:global", 0, 49)
```

### 方式 2：从 MySQL 查询详情

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_items(session: AsyncSession, item_ids: list[str]):
    stmt = select(Item).where(
        Item.id.in_(item_ids),
        Item.status == "published"
    ).order_by(Item.quality_score.desc())
    result = await session.execute(stmt)
    return result.scalars().all()
```

### 方式 3：直接查询 MySQL

```python
# 按分类获取内容
stmt = select(Item).where(
    Item.source_type == "rss",
    Item.category == "tech",
    Item.status == "published"
).order_by(Item.quality_score.desc()).limit(20)
```

## 配置

### Content Supply 端

确保 `configs/app.yaml` 中 MySQL 和 Redis 配置与推荐系统一致：

```yaml
mysql:
  host: "localhost"
  port: 3306
  user: "root"
  password: "your_password"
  database: "rec_platform"

redis:
  host: "localhost"
  port: 6379
  db: 0
```

### 推荐系统端

推荐系统需要：

1. 配置相同的 MySQL 连接
2. 配置相同的 Redis 连接
3. 识别 `cs_` 前缀的表
4. 读取 `item_pool:all` 和 `hot_items:global`

## 数据同步时序

```
Content Supply                          推荐系统
     │                                      │
     ├── SADD item_pool:all {item_id} ────→ │ 召回时读取 SET
     ├── ZADD hot_items:global ────────────→ │ 热门召回读取 ZSET
     ├── INSERT cs_items ─────────────────→ │ 详情查询读取 MySQL
     │                                      │
     ├── DEL (清理时) ─────────────────────→ │ 从 SET/ZSET 移除
     │                                      │
```
