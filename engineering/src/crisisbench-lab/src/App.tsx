import { useEffect, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import {
  BarChart3,
  Coins,
  Images,
  LayoutDashboard,
  Library,
  Radar as RadarIcon,
  Scale,
} from 'lucide-react'
import type { Dataset } from './types'
import { loadDataset } from './lib/data'
import { Skeleton } from './components/ui'
import Overview from './views/Overview'
import LayerCompare from './views/LayerCompare'
import RadarView from './views/RadarView'
import ScenarioExplorer from './views/ScenarioExplorer'
import Judging from './views/Judging'
import CostPanel from './views/CostPanel'
import FigureGallery from './views/FigureGallery'

type TabId = 'overview' | 'layers' | 'radar' | 'scenarios' | 'judging' | 'cost' | 'figures'

const TABS: { id: TabId; label: string; icon: typeof BarChart3 }[] = [
  { id: 'overview', label: '总览', icon: LayoutDashboard },
  { id: 'layers', label: '分层得分', icon: BarChart3 },
  { id: 'radar', label: '雷达对比', icon: RadarIcon },
  { id: 'scenarios', label: '场景浏览', icon: Library },
  { id: 'judging', label: '裁判可靠性', icon: Scale },
  { id: 'cost', label: '成本', icon: Coins },
  { id: 'figures', label: '图表库', icon: Images },
]

export default function App() {
  const [tab, setTab] = useState<TabId>('overview')
  const [data, setData] = useState<Dataset | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDataset()
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  return (
    <div className="flex min-h-full flex-col lg:flex-row">
      <aside className="lg:sticky lg:top-0 lg:h-screen lg:w-60 lg:shrink-0 lg:border-r lg:border-slate-200/80 lg:bg-white/70">
        <div className="flex items-center gap-2.5 px-5 pt-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-sm font-bold text-white shadow-lift">
            CB
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight text-ink-900">CrisisBench</div>
            <div className="text-[11px] text-ink-500">评测可视化平台</div>
          </div>
        </div>

        <nav className="mt-6 flex gap-1.5 overflow-x-auto px-4 pb-3 lg:flex-col lg:overflow-visible lg:px-3 lg:pb-0">
          {TABS.map(({ id, label, icon: Icon }) => {
            const active = tab === id
            return (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`flex shrink-0 items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-brand-soft text-brand'
                    : 'text-ink-700 hover:bg-slate-100'
                }`}
              >
                <Icon size={17} strokeWidth={2.1} />
                {label}
              </button>
            )
          })}
        </nav>

        <div className="mt-auto hidden px-5 py-5 text-[11px] leading-relaxed text-ink-500 lg:block">
          数据取自仓库
          <br />
          research/crisis-bench/results
        </div>
      </aside>

      <main className="min-w-0 flex-1">
        {error && (
          <div className="mx-auto max-w-6xl px-6 py-16">
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800">
              数据没读上来：{error}。确认 public/data 下的 json 是否完整。
            </div>
          </div>
        )}

        {!data && !error && <LoadingState />}

        {data && (
          <AnimatePresence mode="wait">
            {tab === 'overview' && <Overview key="overview" data={data} />}
            {tab === 'layers' && <LayerCompare key="layers" data={data} />}
            {tab === 'radar' && <RadarView key="radar" data={data} />}
            {tab === 'scenarios' && <ScenarioExplorer key="scenarios" data={data} />}
            {tab === 'judging' && <Judging key="judging" data={data} />}
            {tab === 'cost' && <CostPanel key="cost" data={data} />}
            {tab === 'figures' && <FigureGallery key="figures" />}
          </AnimatePresence>
        )}
      </main>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-8 sm:px-8">
      <Skeleton className="h-8 w-56" />
      <Skeleton className="mt-3 h-4 w-80" />
      <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <Skeleton className="mt-6 h-72" />
    </div>
  )
}
