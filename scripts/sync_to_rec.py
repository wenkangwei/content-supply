"""同步 content-supply 内容到 llm-rec-platform 的 Redis。

将 cs_items 表中的内容同步到推荐系统所需的 Redis Key：
  - item_pool:all        SET     全部 item ID
  - hot_items:global     ZSET    {item_id: quality_score}
  - item_feat:{id}       HASH    {item_id, title, category, tags, author, ...}
  - item_sim:{id}        STRING  JSON 相似度列表（基于标签交集）
  - community_hot:{source_type}  ZSET  按来源分区的热门

用法:
  python3.10 scripts/sync_to_rec.py
  python3.10 scripts/sync_to_rec.py --clean    # 清理旧数据后重新同步
  python3.10 scripts/sync_to_rec.py --source rss  # 只同步指定来源
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import redis

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# === 数据读取（同步 SQLite / MySQL） ===

_SQLITE_PATH = ROOT / "content_supply.db"


def _read_items_sqlite(source_type: str | None = None) -> list[dict]:
    """从 SQLite 读取 cs_items。"""
    import sqlite3

    if not _SQLITE_PATH.exists():
        print(f"SQLite 数据库不存在: {_SQLITE_PATH}")
        return []

    conn = sqlite3.connect(str(_SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    try:
        sql = "SELECT * FROM cs_items"
        params = []
        if source_type:
            sql += " WHERE source_type = ?"
            params.append(source_type)
        sql += " ORDER BY quality_score DESC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _read_items_mysql(source_type: str | None = None) -> list[dict]:
    """从 MySQL 读取 cs_items。"""
    try:
        import pymysql
    except ImportError:
        return []

    try:
        conn = pymysql.connect(
            host="localhost", port=3306,
            user="rec_user", password="rec_pass",
            database="rec_platform",
        )
        sql = "SELECT * FROM cs_items"
        params = []
        if source_type:
            sql += " WHERE source_type = %s"
            params.append(source_type)
        sql += " ORDER BY quality_score DESC"
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, params)
            result = cur.fetchall()
        conn.close()
        return result
    except Exception as e:
        print(f"MySQL 读取失败: {e}")
        return []


def read_items(source_type: str | None = None) -> list[dict]:
    """读取所有 items，优先 MySQL，回退 SQLite。"""
    items = _read_items_mysql(source_type)
    if not items:
        items = _read_items_sqlite(source_type)
    return items


# === 相似度计算 ===

def _compute_similarities(items: list[dict], top_k: int = 5) -> dict[str, list]:
    """基于标签交集计算相似度。"""
    # Parse tags
    item_tags: dict[str, set] = {}
    for item in items:
        iid = item["id"]
        raw_tags = item.get("tags", "[]")
        try:
            tags = set(json.loads(raw_tags)) if raw_tags else set()
        except (json.JSONDecodeError, TypeError):
            tags = set()
        item_tags[iid] = tags

    # Also consider source_type and category for similarity
    item_meta: dict[str, tuple] = {}
    for item in items:
        item_meta[item["id"]] = (
            item.get("source_type", ""),
            item.get("category", ""),
        )

    result = {}
    for item in items:
        iid = item["id"]
        my_tags = item_tags[iid]
        my_meta = item_meta[iid]
        sims = []
        for other in items:
            oid = other["id"]
            if oid == iid:
                continue
            other_tags = item_tags[oid]
            # Jaccard similarity on tags
            if my_tags and other_tags:
                intersection = my_tags & other_tags
                union = my_tags | other_tags
                tag_sim = len(intersection) / len(union)
            else:
                tag_sim = 0
            # Bonus for same source_type or category
            other_meta = item_meta[oid]
            meta_sim = 0
            if my_meta[0] and my_meta[0] == other_meta[0]:
                meta_sim += 0.3
            if my_meta[1] and my_meta[1] == other_meta[1]:
                meta_sim += 0.2
            total_sim = min(tag_sim + meta_sim, 0.99)
            if total_sim > 0.1:
                sims.append([oid, round(total_sim, 3)])

        sims.sort(key=lambda x: x[1], reverse=True)
        result[iid] = sims[:top_k]

    return result


# === Redis 写入 ===

def sync_to_redis(
    client: redis.Redis,
    items: list[dict],
    clean: bool = False,
) -> None:
    """同步 items 到 rec-platform Redis 格式。"""
    if not items:
        print("没有数据需要同步")
        return

    if clean:
        _clean_rec_keys(client)

    pipe = client.pipeline(transaction=False)

    print(f"同步 {len(items)} 条内容到 Redis ...")

    # 1. item_pool:all — SET of all item IDs
    print("  1. item_pool:all (SET)")
    pipe.delete("item_pool:all")
    pipe.sadd("item_pool:all", *[it["id"] for it in items])

    # 2. hot_items:global — ZSET {item_id: quality_score}
    print("  2. hot_items:global (ZSET)")
    pipe.delete("hot_items:global")
    for item in items:
        score = float(item.get("quality_score") or 0)
        pipe.zadd("hot_items:global", {item["id"]: score})

    # 3. item_feat:{id} — HASH with metadata
    print("  3. item_feat:{id} (HASH)")
    for item in items:
        feat_key = f"item_feat:{item['id']}"
        mapping = {
            "item_id": item.get("id") or "",
            "title": item.get("title") or "",
            "category": item.get("category") or "",
            "tags": item.get("tags") or "[]",
            "author": item.get("author") or item.get("source_name") or "",
            "source_type": item.get("source_type") or "",
            "image_url": item.get("image_url") or "",
            "score": str(item.get("quality_score") or 0),
            "created_at": str(item.get("created_at") or ""),
        }
        pipe.hset(feat_key, mapping=mapping)

    # 4. item_sim:{id} — JSON similarity list
    print("  4. item_sim:{id} (STRING/JSON)")
    similarities = _compute_similarities(items)
    for iid, sim_list in similarities.items():
        pipe.set(f"item_sim:{iid}", json.dumps(sim_list, ensure_ascii=False))

    # 5. community_hot:{source_type} — ZSET per source_type
    print("  5. community_hot:{source_type} (ZSET)")
    source_groups: dict[str, list] = {}
    for item in items:
        st = item.get("source_type", "unknown")
        source_groups.setdefault(st, []).append(item)
    for st, group in source_groups.items():
        key = f"community_hot:source_{st}"
        pipe.delete(key)
        for item in group:
            score = float(item.get("quality_score") or 0)
            pipe.zadd(key, {item["id"]: score})

    pipe.execute()
    print(f"\n同步完成!")
    print(f"  item_pool:all: {len(items)} 个")
    print(f"  hot_items:global: {len(items)} 个")
    print(f"  item_feat:*: {len(items)} 个")
    print(f"  item_sim:*: {len(similarities)} 个")
    print(f"  community_hot:*: {len(source_groups)} 个分区")
    for st, group in sorted(source_groups.items(), key=lambda x: -len(x[1])):
        print(f"    source_{st}: {len(group)} 个")


def _clean_rec_keys(client: redis.Redis) -> None:
    """清理推荐系统相关的 Redis keys。"""
    print("清理旧数据 ...")
    patterns = [
        "item_pool:all", "hot_items:global",
        "item_feat:*", "item_sim:*",
        "community_hot:source_*",
    ]
    total = 0
    for pattern in patterns:
        if "*" in pattern:
            keys = client.keys(pattern)
        else:
            keys = [pattern]
        if keys:
            deleted = client.delete(*keys)
            total += deleted
    print(f"已清理 {total} 个 key")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="同步内容到推荐系统 Redis")
    parser.add_argument("--clean", action="store_true", help="清理旧数据后重新同步")
    parser.add_argument("--source", type=str, default=None, help="只同步指定来源 (rss/web/jimeng/hot_keyword)")
    args = parser.parse_args()

    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    client.ping()
    print(f"Redis 连接成功 ({REDIS_HOST}:{REDIS_PORT})")

    items = read_items(source_type=args.source)
    print(f"读取到 {len(items)} 条内容")

    sync_to_redis(client, items, clean=args.clean)


if __name__ == "__main__":
    main()
