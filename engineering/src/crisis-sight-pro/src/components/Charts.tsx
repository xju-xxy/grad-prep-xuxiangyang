// 图表区。数据都是从推演结果里算出来的，没写死。

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Radar as RadarIcon, BarChart3, PieChart as PieIcon } from 'lucide-react'
import type { AnalysisResult } from '../engine/types'
import { GlassCard, SectionTitle } from './ui'

const PIE_COLORS = ['#22d3ee', '#818cf8', '#34d399', '#fbbf24', '#f472b6']

// 深色底下的浮层提示，Recharts 默认的太白
function DarkTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="rounded-lg border border-white/10 bg-abyss-700/95 px-3 py-2 text-[12px] shadow-panel backdrop-blur">
      {label !== undefined && (
        <div className="mb-1 text-slate-400">{label}</div>
      )}
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2 tabnum text-slate-100">
          <span
            className="h-2 w-2 rounded-full"
            style={{ background: p.color || p.fill }}
          />
          <span className="text-slate-400">{p.name}</span>
          <span className="font-semibold">{p.value}</span>
        </div>
      ))}
    </div>
  )
}

const axisStyle = { fill: '#7f93b3', fontSize: 11 }
const gridStroke = 'rgba(120,160,220,0.12)'

export function ChartsPanel({ result }: { result: AnalysisResult }) {
  const radarData = result.radar.map((d) => ({ dim: d.name, value: d.value }))
  const timelineData = result.timeline.map((t) => ({ period: t.name, value: t.value }))
  const resourceData = result.resources.map((r) => ({ name: r.name, value: r.value }))

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      {/* 风险维度雷达 */}
      <GlassCard className="p-5">
        <SectionTitle
          icon={<RadarIcon className="h-4 w-4" />}
          title="风险维度画像"
          desc="五个维度按现场描述与知识库危害项打分，满分 100。"
        />
        <div className="mt-3 h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radarData} outerRadius="72%">
              <PolarGrid stroke={gridStroke} />
              <PolarAngleAxis dataKey="dim" tick={axisStyle} />
              <PolarRadiusAxis domain={[0, 100]} tick={axisStyle} stroke={gridStroke} />
              <Radar
                name="风险值"
                dataKey="value"
                stroke="#22d3ee"
                fill="#22d3ee"
                fillOpacity={0.28}
                strokeWidth={2}
              />
              <Tooltip content={<DarkTooltip />} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </GlassCard>

      {/* 分时段处置优先级 */}
      <GlassCard className="p-5">
        <SectionTitle
          icon={<BarChart3 className="h-4 w-4" />}
          title="分时段处置优先级"
          desc="越早的时段越吃紧，数值由整体风险分推出来。"
          accent="#818cf8"
        />
        <div className="mt-3 h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={timelineData} margin={{ top: 10, right: 12, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id="barFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#818cf8" />
                  <stop offset="100%" stopColor="#22d3ee" />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={gridStroke} vertical={false} />
              <XAxis dataKey="period" tick={axisStyle} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={axisStyle} axisLine={false} tickLine={false} />
              <Tooltip content={<DarkTooltip />} cursor={{ fill: 'rgba(129,140,248,0.08)' }} />
              <Bar dataKey="value" name="优先级" fill="url(#barFill)" radius={[6, 6, 0, 0]} maxBarSize={54} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </GlassCard>

      {/* 资源需求占比 */}
      <GlassCard className="p-5 lg:col-span-2">
        <SectionTitle
          icon={<PieIcon className="h-4 w-4" />}
          title="资源需求占比"
          desc="从五个风险维度折算出的资源投放建议，合计 100%。"
          accent="#34d399"
        />
        <div className="mt-3 grid items-center gap-4 sm:grid-cols-[1.1fr_1fr]">
          <div className="h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={resourceData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius="52%"
                  outerRadius="80%"
                  paddingAngle={3}
                  stroke="rgba(11,18,32,0.9)"
                  strokeWidth={2}
                >
                  {resourceData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<DarkTooltip />} />
                <Legend
                  verticalAlign="middle"
                  align="right"
                  layout="vertical"
                  formatter={(v) => <span style={{ color: '#9fb0cc', fontSize: 12 }}>{v}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* 右侧补一份数值条，读数更直观 */}
          <div className="space-y-3">
            {result.resources.map((r, i) => (
              <div key={r.name}>
                <div className="mb-1 flex items-center justify-between text-[12.5px]">
                  <span className="flex items-center gap-2 text-slate-300">
                    <span
                      className="h-2.5 w-2.5 rounded-sm"
                      style={{ background: PIE_COLORS[i % PIE_COLORS.length] }}
                    />
                    {r.name}
                  </span>
                  <span className="tabnum font-semibold text-slate-100">{r.value}%</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${r.value}%`,
                      background: PIE_COLORS[i % PIE_COLORS.length],
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </GlassCard>
    </div>
  )
}
