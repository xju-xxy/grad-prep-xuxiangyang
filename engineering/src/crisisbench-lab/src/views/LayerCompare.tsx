import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Dataset, LayerName } from '../types'
import { configScore, sortedConfigs } from '../lib/data'
import { LAYERS, meta } from '../lib/theme'
import { pct } from '../lib/format'
import { Card, Chip, PageWrap, SectionTitle, SourceNote } from '../components/ui'

export default function LayerCompare({ data }: { data: Dataset }) {
  const { analysis } = data
  const keys = sortedConfigs(analysis)
  const [selected, setSelected] = useState<string[]>(keys)

  const scores = useMemo(
    () => Object.fromEntries(keys.map((k) => [k, configScore(analysis, k)])),
    [analysis, keys],
  )

  const toggle = (k: string) =>
    setSelected((prev) =>
      prev.includes(k) ? (prev.length > 1 ? prev.filter((x) => x !== k) : prev) : [...prev, k],
    )

  const chartData = LAYERS.map((layer) => {
    const row: Record<string, number | string> = { layer }
    for (const k of keys) row[k] = Number(scores[k].layers[layer].score.toFixed(1))
    return row
  })

  return (
    <PageWrap>
      <SectionTitle
        title="分层得分对比"
        desc="把每个配置放到事实 / 推理 / 决策三层上看，柱高是加权命中率"
      />

      <Card className="mb-5 p-4">
        <div className="flex flex-wrap items-center gap-2">
          {keys.map((k) => (
            <Chip key={k} active={selected.includes(k)} color={meta(k).color} onClick={() => toggle(k)}>
              {meta(k).short}
            </Chip>
          ))}
          <button
            onClick={() => setSelected(keys)}
            className="ml-1 text-xs font-medium text-brand hover:underline"
          >
            全选
          </button>
          <button
            onClick={() => setSelected([keys[0]])}
            className="text-xs font-medium text-ink-500 hover:underline"
          >
            只看首个
          </button>
        </div>
      </Card>

      <Card className="p-5">
        <div className="h-[420px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis
                dataKey="layer"
                tickLine={false}
                axisLine={{ stroke: '#E2E8F0' }}
                tick={{ fontSize: 13, fill: '#334155' }}
              />
              <YAxis
                domain={[0, 100]}
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 12, fill: '#64748B' }}
                unit="%"
              />
              <Tooltip
                cursor={{ fill: 'rgba(79,70,229,0.05)' }}
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null
                  return (
                    <div className="rounded-xl border border-slate-200 bg-white/95 p-3 shadow-card backdrop-blur">
                      <div className="mb-2 text-xs font-semibold text-ink-900">{label}</div>
                      <div className="space-y-1.5">
                        {payload.map((p) => {
                          const k = p.dataKey as string
                          const s = scores[k]?.layers[label as LayerName]
                          return (
                            <div key={k} className="flex items-center gap-2 text-xs">
                              <span
                                className="inline-block h-2.5 w-2.5 rounded-sm"
                                style={{ backgroundColor: meta(k).color }}
                              />
                              <span className="text-ink-700">{meta(k).short}</span>
                              <span className="num ml-auto font-medium text-ink-900">
                                {s ? `${s.hit}/${s.total} · ${pct(s.score)}` : '—'}
                              </span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )
                }}
              />
              <Legend
                formatter={(value: string) => (
                  <span style={{ color: '#334155', fontSize: 12 }}>{meta(value).short}</span>
                )}
              />
              {keys
                .filter((k) => selected.includes(k))
                .map((k) => (
                  <Bar key={k} dataKey={k} fill={meta(k).color} radius={[6, 6, 0, 0]} maxBarSize={44} />
                ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <SourceNote>
          来源：results/v0.4-analysis.json 各 config 的 matrix；命中/总数由逐场景三元组累加得到。
        </SourceNote>
      </Card>

      <Card className="mt-6 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80 text-left text-xs text-ink-500">
                <th className="px-4 py-3 font-medium">配置</th>
                {LAYERS.map((l) => (
                  <th key={l} className="px-4 py-3 font-medium">
                    {l}
                  </th>
                ))}
                <th className="px-4 py-3 font-medium">三层总分</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => {
                const s = scores[k]
                return (
                  <tr key={k} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/60">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-block h-2.5 w-2.5 rounded-sm"
                          style={{ backgroundColor: meta(k).color }}
                        />
                        <span className="font-medium text-ink-900">{meta(k).short}</span>
                      </div>
                    </td>
                    {LAYERS.map((l) => (
                      <td key={l} className="num px-4 py-3 text-ink-700">
                        <span className="font-medium text-ink-900">{pct(s.layers[l].score)}</span>
                        <span className="ml-2 text-xs text-ink-500">
                          {s.layers[l].hit}/{s.layers[l].total}
                        </span>
                      </td>
                    ))}
                    <td className="num px-4 py-3 font-semibold text-brand">
                      {pct(s.overall.score)}
                      <span className="ml-2 text-xs font-normal text-ink-500">
                        {s.overall.hit}/{s.overall.total}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </PageWrap>
  )
}
