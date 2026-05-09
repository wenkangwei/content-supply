export const API_BASE = '/'
export const PAGE_SIZE = 20
export const DEBOUNCE_MS = 300

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  rss: 'RSS',
  atom: 'Atom',
  web: '网页',
  hot_search: '热搜',
  hot_keyword: '热搜词',
  manual: '手动',
  jimeng: '即梦',
}

export const PLATFORM_LABELS: Record<string, string> = {
  hackernews: 'Hacker News',
  reddit: 'Reddit',
  google: 'Google Trends',
  twitter: 'Twitter/X',
  baidu: '百度',
  weibo: '微博',
  zhihu: '知乎',
  douyin: '抖音',
}

export const REWRITE_TYPE_LABELS: Record<string, string> = {
  paraphrase: '伪原创',
  summarize: '摘要',
  expand: '扩展',
}

export const STATUS_LABELS: Record<string, string> = {
  active: '运行中',
  paused: '已暂停',
  error: '错误',
  published: '已发布',
  draft: '草稿',
  archived: '已归档',
  pending: '等待中',
  running: '运行中',
  done: '完成',
  failed: '失败',
}
