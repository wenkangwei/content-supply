# CLAUDE.md - Content Supply Web

> 本文件是 AI Agent 的开发指南，所有开发行为必须严格遵守以下规范。

## 项目概述

Content Supply Web 是 Content Supply Platform 的前端界面，提供内容展示、Feed 管理、爬取控制、热搜监控、内容改写、清理管理等功能。

- **技术栈**: React 19 + Vite 8 + TailwindCSS 4 + Zustand 5 + TypeScript 6
- **后端**: FastAPI @ `localhost:8010`
- **前端**: Vite dev server @ `localhost:5173`（API 通过 proxy 转发）

## 开发环境

```bash
cd web
npm install          # 安装依赖
npm run dev          # 启动开发服务器 (localhost:5173)
npm run build        # 构建生产版本
npm run preview      # 预览构建结果
npm run type-check   # TypeScript 类型检查
npm run lint         # ESLint 检查
npm run test         # 运行测试
```

## 项目结构

```
src/
├── api/            # API 请求层（按模块分文件）
│   ├── client.ts   # Axios 实例
│   ├── types.ts    # 所有 TypeScript 类型
│   └── *.ts        # 各模块 API 函数
├── components/
│   ├── layout/     # 布局组件 (Header, Sidebar, MainLayout)
│   ├── ui/         # 基础 UI 组件 (Button, Badge, Spinner, Pagination)
│   └── shared/     # 业务共享组件 (ContentCard)
├── pages/          # 页面组件（每个路由一个文件）
├── stores/         # Zustand 状态管理
├── hooks/          # 自定义 Hooks
├── utils/          # 工具函数
└── styles/         # 全局样式
```

## 编码规范

### 命名
- 组件文件: `PascalCase.tsx` (如 `ContentCard.tsx`)
- API 文件: `camelCase.ts` (如 `feeds.ts`)
- API 函数: 动词+名词 (`getFeeds`, `createFeed`)
- Store: `useXxxStore.ts`
- 事件处理: `handleClick`, `handleSubmit`

### TypeScript
- `strict: true`，禁止 `any`
- 优先 `interface`，联合类型用 `type`
- 所有 API 类型定义在 `src/api/types.ts`
- 使用 path alias `@/` 引用 src 目录

### 样式 (TailwindCSS)
- **禁止**内联 style，一律使用 Tailwind 类
- 暗色主题默认，通过 CSS 变量 (见 `globals.css`)
- 重复 >3 次的类组合提取为组件
- 背景层级: `bg-bg-primary` → `bg-bg-secondary` → `bg-bg-tertiary` → `bg-bg-hover`

### 暗色主题色板
```
--bg-primary:   #060814  页面底色
--bg-secondary: #0f1729  卡片/面板
--bg-tertiary:  #1a2332  hover/子元素
--bg-sidebar:   #0c1021  侧边栏
--text-primary: #e2e8f0  主文字
--text-secondary: #94a3b8  辅助文字
--accent:       #3b82f6  主强调色
--success:      #22c55e
--warning:      #eab308
--danger:       #ef4444
--border:       #1e293b
```

### API 调用
- 所有请求通过 `src/api/client.ts` 的 Axios 实例
- 响应拦截器自动解包 `response.data`
- 错误拦截器统一 Toast 提示
- 每个请求必须有 loading 状态

### 组件结构
1. Props 接口定义
2. Hooks (useState, useEffect, etc.)
3. Handlers
4. JSX render
5. 导出用 named export: `export function Xxx()`

## Git 规范

- Commit: `feat: [F001] 描述` / `fix: [F001] 描述`
- 每个 commit 关联 feature_list.json 中的 ID
- 修复优先于新功能

## 自动化工作流

本项目遵循 agent-harness-framework 范式:
- `feature_list.json` — Feature 跟踪
- `claude-progress.txt` — 进度日志
- `scripts/auto_run.sh` — 自动化脚本
- 每个 session 只做 1 个 Feature
- 端到端测试通过才标记 `passes: true`

## 权限

### 自动执行（无需确认）
- 项目内文件的增删改
- `npm run dev/build/test/lint`
- `git add/commit`
- `npm install`

### 需要确认
- `rm -rf` 操作
- `pip install` 或系统级安装
- 修改项目外文件
- `git push`
