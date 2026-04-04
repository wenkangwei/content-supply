# 内容改写

本案例展示如何使用 LLM 对入库内容进行改写。

## 场景

你需要对采集的原始内容进行伪原创处理，规避版权风险。

## 前提条件

- LLM 服务已启动（Ollama / vLLM / OpenAI）
- `configs/app.yaml` 中已配置 LLM 参数

```yaml
llm:
  base_url: "http://localhost:11434/v1"
  api_key: "ollama"
  model: "qwen2.5:7b"
```

## 改写单个内容

```bash
# 查看待改写内容
curl "http://localhost:8010/items?source_type=rss&page_size=5"

# 选择一条进行改写
curl -X POST http://localhost:8010/rewrite/{item_id} \
  -H "Content-Type: application/json" \
  -d '{"rewrite_type": "paraphrase"}'
```

## 批量改写

```bash
# 对所有 RSS 内容批量改写（最多 10 条）
curl -X POST http://localhost:8010/rewrite/batch \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "rss",
    "rewrite_type": "paraphrase",
    "limit": 10
  }'
```

## 验证改写结果

```bash
# 查看改写后的内容
curl http://localhost:8010/items/{item_id}
```

改写后：

- `content` — 改写后的正文
- `original_content` — 原始正文（备份）
- `is_rewritten` — `true`
- `rewrite_task_id` — 关联改写任务

## 改写模式选择

| 模式 | 适用场景 | Prompt 策略 |
|------|----------|-------------|
| paraphrase | 版权规避 | 重新表述，保持主旨 |
| summarize | 长文精简 | 提取核心信息 |
| expand | 短文扩充 | 添加细节和背景 |

## 数据流

```
选择待改写内容
    ↓
ContentRewriter → 构建 prompt → 调用 LLM API
    ↓
原文备份到 original_content
    ↓
改写结果写入 content
    ↓
更新 is_rewritten = true
    ↓
更新 Redis 质量分
```
