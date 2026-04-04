# 核心能力

Content Supply Platform 提供 8 大核心能力，覆盖内容从采集到管理的全生命周期。

## 能力矩阵

| 能力 | 说明 | 模块 |
|------|------|------|
| RSS 订阅抓取 | 定期轮询 RSS/Atom feed，自动解析入库 | RSSCrawler |
| 通用网页抓取 | 任意 URL 正文/图片提取 | WebScraper |
| 热搜词采集 | 多平台热搜词实时采集 | HotTracker |
| 热点内容抓取 | 按热搜词搜索并抓取相关文章 | HotContentFetcher |
| LLM 内容改写 | 多模式改写，规避版权风险 | ContentRewriter |
| 内容处理 | 去重、标签提取、质量评分 | ContentProcessor |
| 内容池管理 | 单池多标签，灵活路由 | ItemWriter |
| 过期清理 | 多策略审核制清理 | CleanupManager |

## RSS 订阅抓取

!!! info "对应模块"
    `content_supply.services.rss_crawler.RSSCrawler`

- 支持 RSS 2.0 和 Atom 格式
- 自动提取标题、摘要、正文、作者、发布时间、图片、标签
- 错误容忍：单条目解析失败不影响整批处理
- 定时轮询：每个 Feed 独立配置轮询间隔

## 通用网页抓取

!!! info "对应模块"
    `content_supply.services.web_scraper.WebScraper`

- 基于 trafilatura 的高质量正文提取
- **微信公众号文章**：专用提取器，从 `js_content` div 提取正文，支持标题/作者/日期
- 自动提取 og:image 封面图
- 不支持的 URL 返回友好提示（如后台页面、登录页面、非HTML文件）
- robots.txt 合规检查（手动抓取时跳过）
- 并发控制：信号量限制同时抓取数量

## 热搜词采集

!!! info "对应模块"
    `content_supply.services.hot_tracker.HotTracker`

支持 8 个平台：

| 平台 | 类型 | 说明 |
|------|------|------|
| Hacker News | 国际 | 科技社区热门 |
| Reddit | 国际 | 综合社区热门 |
| Google Trends | 国际 | 搜索趋势 |
| Twitter/X | 国际 | 社交热门 |
| 百度热搜 | 国内 | 搜索热搜 |
| 微博热搜 | 国内 | 社交热搜 |
| 知乎热榜 | 国内 | 问答热门 |
| 抖音热点 | 国内 | 短视频热门 |

## LLM 内容改写

!!! info "对应模块"
    `content_supply.services.content_rewriter.ContentRewriter`

三种改写模式：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `paraphrase` | 伪原创改写 | 规避版权，保持内容主旨 |
| `summarize` | 摘要生成 | 长文精简，信息提炼 |
| `expand` | 内容扩展 | 短文扩充，增加信息量 |

支持任何 OpenAI-compatible API：Ollama、vLLM、OpenAI。

## 内容处理

!!! info "对应模块"
    `content_supply.services.content_processor.ContentProcessor`

### 去重

- URL 精确匹配去重
- SHA256 内容哈希去重（即使 URL 不同，内容相同也会被拦截）

### 标签提取

- 英文关键词提取（基于词频）
- 中文关键词提取（基于字符 bigram）
- 自动去重和清洗

### 质量评分

多维度评分，满分 1.0：

| 维度 | 权重 | 说明 |
|------|------|------|
| 内容长度 | 0-0.3 | 正文越长分越高 |
| 图片质量 | 0-0.2 | 有封面图加分 |
| 来源信誉 | 0-0.2 | RSS 来源优于网页抓取 |
| 标签丰富度 | 0-0.3 | 标签越多分越高 |

## 内容池管理

- 单池设计：所有内容存入 `cs_items` 表
- 多标签路由：通过 `source_type` + `category` + `tags` 灵活筛选
- Redis 同步：入库同时推送 ID 到 `item_pool:all`（SET）和 `hot_items:global`（ZSET）
- 推荐系统直接从 Redis 召回内容 ID，再到 MySQL 查详情

## 过期清理

!!! info "对应模块"
    `content_supply.services.cleanup_manager.CleanupManager`

四种清理策略：

| 策略 | 说明 |
|------|------|
| TTL 过期 | 按 source_type 配置天数过期 |
| 容量淘汰 | 超出上限时淘汰低质量旧内容 |
| 质量淘汰 | 低于质量阈值的内容被清理 |
| 冷启动失败 | 入库后无曝光无点击的内容加速淘汰 |

!!! warning "审核制"
    所有清理操作采用**审核制**：扫描 → 生成待删清单 → 通知审核 → 确认后删除。支持自动超时确认。

## 通知集成

支持多种通知渠道：

- **Webhook** — 通用 HTTP POST
- **企业微信** — WeCom Bot API
- **飞书** — Feishu Bot API
- **钉钉** — DingTalk Bot API
