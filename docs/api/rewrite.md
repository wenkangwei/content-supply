# 内容改写 API

使用 LLM 对内容进行改写操作。

## 改写单个内容

```
POST /rewrite/{item_id}
```

### 请求体

```json
{
  "rewrite_type": "paraphrase"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| rewrite_type | string | ✅ | paraphrase / summarize / expand |

### 响应示例

```json
{
  "task_id": 1,
  "item_id": "a1b2c3",
  "rewrite_type": "paraphrase",
  "status": "done",
  "llm_model": "qwen2.5:7b",
  "message": "Rewrite completed"
}
```

## 批量改写

```
POST /rewrite/batch
```

### 请求体

```json
{
  "source_type": "rss",
  "rewrite_type": "paraphrase",
  "limit": 10
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| source_type | string | ❌ | 按来源类型筛选待改写内容 |
| rewrite_type | string | ✅ | paraphrase / summarize / expand |
| limit | int | ❌ | 最多处理条数，默认 10 |

### 响应示例

```json
{
  "tasks_created": 8,
  "rewrite_type": "paraphrase",
  "message": "Batch rewrite triggered for 8 items"
}
```

## 改写模式说明

| 模式 | 说明 |
|------|------|
| paraphrase | 伪原创改写，保持内容主旨 |
| summarize | 摘要生成，长文精简 |
| expand | 内容扩展，短文扩充 |

## 前提条件

- 需要配置 LLM API（`configs/app.yaml` 中的 `llm` 部分）
- 内容必须有正文（`content` 非空）
