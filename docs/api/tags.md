# 标签挖掘 API

> 当前为占位接口，核心逻辑待后续迭代。

## 触发标签挖掘

```
POST /tags/mine
```

### 响应

```json
{
  "status": "accepted",
  "message": "Tag mining triggered"
}
```

返回 HTTP 202，表示任务已接受但尚未完成。

## 查看挖掘状态

```
GET /tags/status
```

### 响应

```json
{
  "status": "idle",
  "last_run": null,
  "items_processed": 0
}
```
