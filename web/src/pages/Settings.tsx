import { useState } from 'react'
import { Settings as SettingsIcon } from 'lucide-react'

export function Settings() {
  const [apiUrl, setApiUrl] = useState('http://localhost:8010')

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-6 text-2xl font-bold text-text-primary">设置</h1>
      <div className="max-w-lg space-y-6">
        <div className="rounded-xl border border-border bg-bg-secondary p-5">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-text-primary">
            <SettingsIcon className="h-4 w-4" /> API 连接
          </h2>
          <div>
            <label className="mb-1 block text-xs text-text-muted">后端 API 地址</label>
            <input
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="h-10 w-full rounded-lg border border-border bg-bg-primary px-3 text-sm text-text-primary focus:border-accent focus:outline-none"
            />
            <p className="mt-1 text-xs text-text-muted">开发环境由 Vite proxy 自动转发，此处仅作显示</p>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-bg-secondary p-5">
          <h2 className="mb-3 text-sm font-medium text-text-primary">关于</h2>
          <div className="space-y-1 text-xs text-text-secondary">
            <p>Content Supply Web v1.0.0</p>
            <p>前端: React + Vite + TailwindCSS</p>
            <p>后端: FastAPI @ localhost:8010</p>
          </div>
        </div>
      </div>
    </div>
  )
}
