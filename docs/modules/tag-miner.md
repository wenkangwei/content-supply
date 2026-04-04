# 标签挖掘

Tag Miner 模块负责定期分析入库内容，使用 LLM 挖掘和优化标签特征。

## 当前状态

!!! info "占位模块"
    Tag Miner 当前为**接口占位**状态，提供 API 接口但核心逻辑待后续迭代实现。

## API

### 触发标签挖掘

```bash
curl -X POST http://localhost:8010/tags/mine
```

返回 `202 Accepted`，表示任务已接受。

### 查看任务状态

```bash
curl http://localhost:8010/tags/status
```

```json
{
  "status": "idle",
  "last_run": null,
  "items_processed": 0
}
```

## 规划中的功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| LLM 标签分析 | 使用 LLM 对内容进行深度标签分析 | P1 |
| 标签聚合 | 统计高频标签，识别趋势 | P2 |
| 标签推荐 | 基于内容特征自动推荐标签 | P2 |
| 标签质量评估 | 评估现有标签的准确性和完整性 | P3 |
| 标签层级构建 | 构建「大类 → 子类 → 标签」层级关系 | P3 |
