import { useMemo, useState } from 'react'
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import type { Dataset } from '../types'
import { categoryScore, configScore, sortedConfigs } from '../lib/data'
import { LAYERS, meta } from '../lib/theme'
import { pct } from '../lib/format'
import { Card, Chip, PageWrap, SectionTitle, SourceNote } from '../components/ui'

type Mode = 'layer' | 'category'

export default function RadarView({ data }: { data: Dataset }) {
  const { analysis, scenarios } = data
  const keys = sortedConfigs(analysis)
  const [mode, setMode] = useState<Mode>('layer')
  const [selected, setSelected] = useState<string[]>(keys)

  const dims = useMemo(() => {
    if (mode === 'layer') return [...LAYERS, '三层总分']
    return [...new Set(scenarios.scenarios.map((s) => s.category))]
  }, [mode, scenarios])

  const chartData = useMemo(
    () =>
      dims.map((dim) => {
        const row: Record<string, number | string> = { dim }
        for (const k of keys) {
          const v =
            mode === 'layer'
              ? dim === '三层总分'
                ? configScore(analysis, k).overall.score
                : configScore(analysis, k).layers[dim as (typeof LAYERS)[number]].score
              : categoryScore(analysis, k, scenarios.scenarios, dim).score
          row[k] = Number(v.toFixed(1))
        }
        return row
      }),
    [dims, keys, mode, analysis, scenarios],
  )

  const toggle = (k: string) =>
    setSelected((prev) =>
      prev.includes(k) ? (prev.length > 1 ? prev.filter((x) => x !== k) : prev) : [...prev, k],
    )

  return (
    <PageWrap>
      <SectionTitle
        title="雷达对比"
        desc="同一张网里叠多个配置，越靠外得分越高"
        right={
          <div className="flex gap-1 rounded-xl border border-slate-200 bg-white p-1">
            {(['layer', 'category'] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  mode === m ? 'bg-brand text-white' : 'text-ink-700 hover:bg-slate-100'
                }`}
              >
                {m === 'layer' ? '三层 + 总分' : '按场景类别'}
              </button>
            ))}
          </div>
        }
      />

      <Card className="mb-5 p-4">
        <div className="flex flex-wrap items-center gap-2">
          {keys.map((k) => (
            <Chip key={k} active={selected.includes(k)} color={meta(k).color} onClick={() => toggle(k)}>
              {meta(k).short}
            </Chip>
          ))}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card className="p-5">
          <div className="h-[440px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={chartData} outerRadius="72%">
                <PolarGrid stroke="#E2E8F0" />
                <PolarAngleAxis dataKey="dim" tick={{ fontSize: 12, fill: '#334155' }} />
                <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#94A3B8' }} angle={90} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null
                    return (
                      <div className="rounded-xl border border-slate-200 bg-white/95 p-3 shadow-card">
                        <div className="mb-2 text-xs font-semibold text-ink-900">
                          {payload[0]?.payload?.dim}
                        </div>
                        <div className="space-y-1.5">
                          {payload.map((p) => (
                            <div key={p.dataKey as string} className="flex items-center gap-2 text-xs">
                              <span
                                className="inline-block h-2.5 w-2.5 rounded-full"
                                style={{ backgroundColor: meta(p.dataKey as string).color }}
                              />
                              <span className="text-ink-700">{meta(p.dataKey as string).short}</span>
                              <span className="num ml-auto font-medium text-ink-900">
                                {pct(p.value as number)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  }}
                />
                {keys
                  .filter((k) => selected.includes(k))
                  .map((k) => (
                    <Radar
                      key={k}
                      dataKey={k}
                      stroke={meta(k).color}
                      fill={meta(k).color}
                      fillOpacity={0.08}
                      strokeWidth={2}
                      dot={{ r: 2.5, fill: meta(k).color }}
                    />
                  ))}
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <SourceNote>
            来源：results/v0.4-analysis.json。三层 + 总分由 matrix 累加；按类别按场景的
            链式 / 单灾种 / 信息矛盾分组累加。
          </SourceNote>
        </Card>

        <Card className="p-5">
          <SectionTitle title={mode === 'layer' ? '各维度数值' : '各类别数值'} />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs text-ink-500">
                  <th className="py-2 pr-3 font-medium">配置</th>
                  {dims.map((d) => (
                    <th key={d} className="py-2 pr-3 font-medium">
                      {d}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {keys.map((k) => (
                  <tr key={k} className="border-b border-slate-100 last:border-0">
                    <td className="py-2 pr-3">
                      <span
                        className="mr-2 inline-block h-2.5 w-2.5 rounded-sm align-middle"
                        style={{ backgroundColor: meta(k).color }}
                      />
                      <span className="text-ink-700">{meta(k).short}</span>
                    </td>
                    {chartData.map((row) => (
                      <td key={String(row.dim)} className="num py-2 pr-3 text-ink-900">
                        {pct(row[k] as number)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {mode === 'category' && (
            <p className="mt-3 text-xs text-ink-500">
              场景类别共三类：链式、单灾种、信息矛盾。分布见场景浏览页。
            </p>
          )}
        </Card>
      </div>
    </PageWrap>
  )
}
