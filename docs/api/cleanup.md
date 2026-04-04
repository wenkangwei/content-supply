# 清理管理 API

管理内容过期清理策略和执行。

## 查看清理策略

```
GET /cleanup/policies
```

### 响应示例

```json
{
  "policies": [
    {
      "source_type": "rss",
      "ttl_days": 30,
      "max_items": 10000,
      "min_quality": 0.2
    },
    {
      "source_type": "hot_keyword",
      "ttl_days": 7,
      "max_items": 5000,
      "min_quality": 0.3,
      "cold_start_ttl_days": 3
    }
  ]
}
```

## 触发清理扫描

```
POST /cleanup/trigger
```

仅生成待删清单，**不会直接删除**任何内容。

### 响应示例

```json
{
  "scan_results": [
    {
      "policy": "ttl",
      "source_type": "rss",
      "items_scanned": 500,
      "items_to_delete": 15
    }
  ],
  "total_pending": 15,
  "message": "Scan completed, pending review"
}
```

## 查看待审核清单

```
GET /cleanup/pending
```

### 响应示例

```json
{
  "pending": [
    {
      "id": 1,
      "policy": "ttl",
      "source_type": "rss",
      "status": "pending_review",
      "items_to_delete": 15,
      "auto_confirm_at": "2026-04-05T03:00:00",
      "created_at": "2026-04-04T03:00:00"
    }
  ]
}
```

## 确认删除

```
POST /cleanup/{log_id}/confirm
```

执行删除操作，同步清理 MySQL 和 Redis。

### 响应示例

```json
{
  "log_id": 1,
  "status": "done",
  "items_deleted": 15,
  "space_freed_mb": 2.5,
  "message": "Cleanup executed"
}
```

## 拒绝删除

```
POST /cleanup/{log_id}/reject
```

拒绝清理，该批内容不会被删除。

### 响应示例

```json
{
  "log_id": 1,
  "status": "rejected",
  "message": "Cleanup rejected"
}
```

## 清理日志

```
GET /cleanup/logs
```

### 查询参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| skip | int | 0 | 跳过条数 |
| limit | int | 20 | 返回条数 |
