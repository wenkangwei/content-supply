# 路线图

## 当前版本：v1.0（已完成）

32 个功能点全部完成，66 个测试通过。核心功能包括 RSS 抓取、网页抓取、热搜词采集、LLM 改写、内容池管理、过期清理等。

---

## v1.1 — 安全加固 & 稳定性（优先级：P1）

> 预计工时：3-5 天

### F032 — 安全加固

| 项目 | 说明 |
|------|------|
| API 认证 | API Key / Bearer Token 中间件，保护所有端点 |
| 输入校验 | `sort_by` 白名单、`status` Enum 校验、`rewrite_type` 校验 |
| 速率限制 | crawl/rewrite/cleanup 等重操作端点限速 |
| CORS | 配置 CORS 中间件 |
| 日志脱敏 | webhook token 不写入日志 |

### F035 — 基础设施

| 项目 | 说明 |
|------|------|
| 健康检查 | `/api/health` 增加 DB/Redis/LLM 连通性检查 |
| 数据库迁移 | 引入 Alembic 管理表结构变更 |
| 优雅停机 | Scheduler `shutdown(wait=True)` |
| UTC 时间 | 统一 `datetime.now(timezone.utc)` |
| 依赖修复 | `aiosqlite` 加入 pyproject.toml |

### F036 — 测试补全

| 项目 | 说明 |
|------|------|
| API 测试 | 所有端点的 HTTP 状态码/响应格式测试 |
| 服务单测 | FeedManager / CleanupManager / NotificationService |
| 边界测试 | 空内容、重复 URL、Redis 失败降级 |

---

## v1.2 — 性能 & 中文优化（优先级：P2）

> 预计工时：3-5 天

### F033 — 性能优化

| 项目 | 说明 |
|------|------|
| 批量写入 | `ItemWriter.write_batch` 批量去重查询 + bulk insert |
| 异步阻塞修复 | `feedparser.parse` 用 `asyncio.to_thread()` 包裹 |
| HTTP 复用 | WebScraper 复用 httpx.AsyncClient 单例 |
| 批量删除 | CleanupManager 批量 `DELETE WHERE id IN (...)` |
| 内容哈希 | 改为全文本 SHA256（非仅前 1000 字符） |

### F034 — 中文内容优化

| 项目 | 说明 |
|------|------|
| jieba 分词 | 中文关键词提取使用 jieba 替代 bigram |
| 质量评分 | 适配中文内容长度标准 |

### F037 — API 增强

| 项目 | 说明 |
|------|------|
| 分页元数据 | Items 列表返回 `{items, total, page, page_size}` |
| 国内热搜适配器 | 实现百度/微博/知乎/抖音适配器 |
| API 版本化 | 路由加 `/v1/` 前缀 |
| 新端点 | `DELETE /items/{id}`、`GET /rewrite/tasks/{id}` |

---

## v1.3 — Playwright 浏览器抓取（优先级：P2）

> 预计工时：5-7 天

### F031 — Playwright 浏览器抓取

这是解决 JS 渲染页面抓取的核心方案。

#### 架构设计

```
URL 输入
    ↓
WebScraper（trafilatura）
    ↓ 内容为空/过短？
PlaywrightScraper（headless browser）
    ↓ 渲染完成
提取正文 → 返回 CrawledItem
```

#### 核心能力

| 能力 | 说明 |
|------|------|
| JS 渲染 | 对 SPA/动态加载页面，等待内容加载完成后提取 |
| Agent 模拟 | 模拟真实浏览器行为：Cookie、滚动、点击「阅读更多」 |
| 微信公众号 | 处理登录态模拟、图文展开、阅读原文跳转 |
| 智能等待 | 等待关键 DOM 元素出现（如 `js_content`） |
| 自动降级 | trafilatura 失败时自动切换到 Playwright |

#### 配置

```yaml
playwright:
  enabled: true
  headless: true
  browser: "chromium"         # chromium / firefox / webkit
  timeout: 30                 # 页面加载超时（秒）
  wait_for: "networkidle"     # 等待策略: domcontentloaded / load / networkidle
  max_concurrent: 3           # 最大并发浏览器实例
  fallback: true              # trafilatura 失败时自动降级

  # Agent 模拟配置
  agent:
    user_agent: "Mozilla/5.0 ..."  # 浏览器 UA
    viewport: {width: 1920, height: 1080}
    locale: "zh-CN"
    timezone: "Asia/Shanghai"

  # 微信公众号专用
  wechat:
    wait_for_selector: "#js_content"
    scroll_to_load: true      # 滚动加载更多
    expand_read_more: true    # 点击「阅读全文」
```

#### 技术方案

- **playwright** (async) — 浏览器自动化
- **playwright-stealth** — 反检测插件
- **上下文复用** — BrowserContext 池化，避免频繁创建
- **资源控制** — 拦截图片/CSS/字体加载，只关注 HTML

---

## 远期规划

| 版本 | 内容 | 时间 |
|------|------|------|
| v2.0 | 标签挖掘引擎（LLM 深度分析）、推荐系统联动、内容分发 | 后续迭代 |
