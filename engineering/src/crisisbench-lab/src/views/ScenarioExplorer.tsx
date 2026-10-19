import { useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Search, X } from 'lucide-react'
import type { Dataset, Scenario } from '../types'
import { sceneScore, sortedConfigs, uniqueSorted } from '../lib/data'
import { CATEGORY_COLORS, LAYERS, meta } from '../lib/theme'
import { pct } from '../lib/format'
import { Card, Chip, PageWrap, SectionTitle, SourceNote } from '../components/ui'

function scoreTone(v: number) {
  if (v >= 90) return 'text-teal-600'
  if (v >= 75) return 'text-brand'
  if (v >= 60) return 'text-amber-600'
  return 'text-rose-600'
}

export default function ScenarioExplorer({ data }: { data: Dataset }) {
  const { analysis, scenarios } = data
  const keys = sortedConfigs(analysis)
  const [q, setQ] = useState('')
  const [cat, setCat] = useState<string>('全部')
  const [disaster, setDisaster] = useState<string>('全部')
  const [open, setOpen] = useState<Scenario | null>(null)

  const categories = ['全部', ...uniqueSorted(scenarios.scenarios.map((s) => s.category))]
  const disasters = ['全部', ...uniqueSorted(scenarios.scenarios.map((s) => s.disaster))]

  const list = useMemo(() => {
    const kw = q.trim().toLowerCase()
    return scenarios.scenarios.filter((s) => {
      if (cat !== '全部' && s.category !== cat) return false
      if (disaster !== '全部' && s.disaster !== disaster) return false
      if (!kw) return true
      return (
        s.id.toLowerCase().includes(kw) ||
        s.disaster.toLowerCase().includes(kw) ||
        s.intel.some((t) => t.toLowerCase().includes(kw))
      )
    })
  }, [q, cat, disaster, scenarios])

  return (
    <PageWrap>
      <SectionTitle
        title="场景浏览"
        desc={`评测集共 ${scenarios.scenarios.length} 个场景，按类别和灾种筛，点开看三层要点与该场景各配置得分`}
      />

      <Card className="mb-5 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[220px] flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-300" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="搜场景编号、灾种或情报关键词…"
              className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-2 pl-9 pr-3 text-sm outline-none transition focus:border-brand/40 focus:bg-white focus:ring-2 focus:ring-brand/15"
            />
          </div>
          <select
            value={disaster}
            onChange={(e) => setDisaster(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-ink-700 outline-none focus:border-brand/40">
            {disasters.map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {categories.map((c) => (
            <Chip
              key={c}
              active={cat === c}
              color={CATEGORY_COLORS[c]}
              onClick={() => setCat(c)}
            >
              {c}
              {c !== '全部' && (
                <span className="num ml-0.5 opacity-70">
                  {scenarios.scenarios.filter((s) => s.category === c).length}
                </span>
              )}
            </Chip>
          ))}
          <span className="ml-auto text-xs text-ink-500">命中 {list.length} 个场景</span>
        </div>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {list.map((s) => {
          const sc = sceneScore(analysis, keys[0], s.id)
          return (
            <motion.button
              key={s.id}
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              onClick={() => setOpen(s)}
              className="group flex flex-col rounded-2xl border border-slate-200/80 bg-white p-4 text-left shadow-card transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-lift"
            >
              <div className="flex items-center justify-between">
                <span className="num text-sm font-semibold text-ink-900">{s.id}</span>
                <span
                  className="rounded-md px-2 py-0.5 text-[11px] font-medium text-white"
                  style={{ backgroundColor: CATEGORY_COLORS[s.category] ?? '#64748B' }}
                >
                  {s.category}
                </span>
              </div>
              <div className="mt-2 text-base font-semibold tracking-tight text-ink-900">
                {s.disaster}
              </div>
              <div className="mt-1 text-xs text-ink-500">{s.timePoint}</div>
              <div className="mt-3 line-clamp-2 text-xs leading-relaxed text-ink-700">
                {s.intel[0]}
              </div>
              <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3">
                <span className="text-[11px] text-ink-500">
                  {s.rubric.事实层.length + s.rubric.推理层.length + s.rubric.决策层.length} 条要点
                </span>
                <span className={`num text-xs font-medium ${scoreTone(sc.score)}`}>
                  {meta(keys[0]).short} {pct(sc.score)}
                </span>
              </div>
            </motion.button>
          )
        })}
      </div>

      {list.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 py-16 text-center text-sm text-ink-500">
          没筛出场景，换个关键词或灾种试试。
        </div>
      )}

      <AnimatePresence>{open && <ScenarioModal key="m" scenario={open} data={data} onClose={() => setOpen(null)} />}</AnimatePresence>
    </PageWrap>
  )
}

function ScenarioModal({
  scenario,
  data,
  onClose,
}: {
  scenario: Scenario
  data: Dataset
  onClose: () => void
}) {
  const { analysis } = data
  const keys = sortedConfigs(analysis)
  const rgb = CATEGORY_COLORS[scenario.category] ?? '#64748B'

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-50 flex justify-end bg-ink-900/30 backdrop-blur-sm"
    >
      <motion.div
        initial={{ x: 40, opacity: 0.6 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 40, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 320, damping: 34 }}
        onClick={(e) => e.stopPropagation()}
        className="h-full w-full max-w-2xl overflow-y-auto bg-white shadow-2xl"
      >
        <div className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 px-6 py-4 backdrop-blur">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="num text-lg font-semibold text-ink-900">{scenario.id}</span>
                <span
                  className="rounded-md px-2 py-0.5 text-[11px] font-medium text-white"
                  style={{ backgroundColor: rgb }}
                >
                  {scenario.category}
                </span>
                <span className="text-sm text-ink-700">{scenario.disaster}</span>
              </div>
              <div className="mt-1 text-xs text-ink-500">{scenario.timePoint}</div>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-ink-500 transition hover:bg-slate-100 hover:text-ink-900"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="space-y-6 px-6 py-5">
          <section>
            <h3 className="mb-2 text-sm font-semibold text-ink-900">该场景各配置得分</h3>
            <div className="space-y-2">
              {keys.map((k) => {
                const sc = sceneScore(analysis, k, scenario.id)
                return (
                  <div key={k} className="flex items-center gap-3">
                    <span className="w-28 shrink-0 text-xs text-ink-700">{meta(k).short}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${sc.score}%`, backgroundColor: meta(k).color }}
                      />
                    </div>
                    <span className={`num w-24 shrink-0 text-right text-xs ${scoreTone(sc.score)}`}>
                      {pct(sc.score)}
                      <span className="ml-1 text-ink-500">
                        {sc.hit}/{sc.total}
                      </span>
                    </span>
                  </div>
                )
              })}
            </div>
            <SourceNote>来源：results/v0.4-analysis.json 的 matrix["{scenario.id}"]。</SourceNote>
          </section>

          {(['情报', '资源'] as const).map((field) => (
            <section key={field}>
              <h3 className="mb-2 text-sm font-semibold text-ink-900">
                {field}
                <span className="num ml-2 text-xs font-normal text-ink-500">
                  {(field === '情报' ? scenario.intel : scenario.resources).length} 条
                </span>
              </h3>
              <ul className="space-y-1.5">
                {(field === '情报' ? scenario.intel : scenario.resources).map((t, i) => (
                  <li key={i} className="flex gap-2 rounded-lg bg-slate-50/70 px-3 py-2 text-xs leading-relaxed text-ink-700">
                    <span className="num text-ink-300">{i + 1}</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </section>
          ))}

          {LAYERS.map((layer) => (
            <section key={layer}>
              <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink-900">
                {layer}
                <span className="num text-xs font-normal text-ink-500">
                  {scenario.rubric[layer].length} 条
                </span>
              </h3>
              <ol className="space-y-2">
                {scenario.rubric[layer].map((r, i) => (
                  <li key={i} className="rounded-xl border border-slate-100 px-4 py-3 text-sm leading-relaxed text-ink-700">
                    <span className="num mr-2 text-xs text-ink-300">{i + 1}</span>
                    {r.point}
                    {r.from && (
                      <div className="mt-1.5 flex flex-wrap gap-1.5 text-[11px]">
                        <span className="rounded bg-brand-soft px-1.5 py-0.5 text-brand">起点 {r.from}</span>
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-ink-700">机制 {r.mech}</span>
                        <span className="rounded bg-teal-50 px-1.5 py-0.5 text-teal-600">终点 {r.to}</span>
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            </section>
          ))}
          <SourceNote>场景原文：scenarios/scenarios.json。</SourceNote>
        </div>
      </motion.div>
    </motion.div>
  )
}
