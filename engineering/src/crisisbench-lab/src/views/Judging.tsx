import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { AdjudicationRow, Dataset } from '../types'
import { adjudicationStat, judgeAgreement } from '../lib/data'
import { pct } from '../lib/format'
import { Card, PageWrap, SectionTitle, SourceNote, StatCard } from '../components/ui'

const kappaTone = (v: number) => {
  if (v < 0) return { text: 'text-rose-600', bg: 'bg-rose-50', label: '几乎无一致性' }
  if (v < 0.2) return { text: 'text-amber-600', bg: 'bg-amber-50', label: '一致性很弱' }
  if (v < 0.4) return { text: 'text-brand', bg: 'bg-brand-soft', label: '一般' }
  return { text: 'text-teal-600', bg: 'bg-teal-50', label: '较好' }
}

export default function Judging({ data }: { data: Dataset }) {
  const { analysis, adjudication } = data
  const stat = adjudicationStat(adjudication)
  const agreement = judgeAgreement(adjudication)
  const kappa = Object.entries(analysis.kappa)
  const selfConsistency = Object.entries(analysis.self_consistency)

  return (
    <PageWrap>
      <SectionTitle
        title="裁判可靠性"
        desc="三裁判多数票到底靠不靠谱？这里看裁判之间的分歧、人工终裁，以及一致性指标"
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="裁判分歧条目" value={stat.total} unit="条" hint="进入人工裁定的要点" />
        <StatCard label="人工复核确认" value={stat.reviewed} unit="条" hint="标注人逐条回查过" tone="teal" />
        <StatCard
          label="被改判条目"
          value={stat.disputed}
          unit="条"
          hint="多数票与人工终裁不一致"
          tone="amber"
        />
        <StatCard
          label="多数票 vs 终裁"
          value={pct(agreement.find((a) => a.rater === '三裁判多数票')?.rate ?? 0)}
          hint="人工裁定为基准"
          tone="pink"
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <SectionTitle title="各裁判与人工终裁的一致率" desc="同一批分歧条目，谁更接近人工裁定" />
          <div className="h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={agreement.map((a) => ({ name: a.rater, rate: Number(a.rate.toFixed(1)), agree: a.agree, total: a.total }))}
                layout="vertical"
                margin={{ left: 8, right: 44, top: 4, bottom: 4 }}
              >
                <XAxis type="number" domain={[0, 100]} hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={126}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 12, fill: '#334155' }}
                />
                <Tooltip
                cursor={{ fill: 'rgba(79,70,229,0.06)' }}
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null
                  const p = payload[0].payload as { name: string; rate: number; agree: number; total: number }
                  return (
                    <div className="rounded-xl border border-slate-200 bg-white/95 px-3 py-2 text-xs shadow-card">
                      <span className="text-ink-700">{p.name}</span>
                      <span className="num ml-2 font-medium text-ink-900">
                        {p.rate}%（{p.agree}/{p.total}）
                      </span>
                    </div>
                  )
                }}
              />
                <Bar dataKey="rate" radius={[0, 6, 6, 0]} barSize={20} fill="#4F46E5">
                  {agreement.map((a, i) => (
                    <Cell key={a.rater} fill={['#4F46E5', '#0D9488', '#7C3AED', '#D97706'][i % 4]} />
                  ))}
                  <LabelList
                    dataKey="rate"
                    position="right"
                    formatter={(v: number) => `${v}%`}
                    style={{ fontSize: 12, fill: '#334155', fontVariantNumeric: 'tabular-nums' }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <SourceNote>来源：results/adjudication.json，人工终裁取「裁定」列，与各裁判逐条比对。</SourceNote>
        </Card>

        <Card className="p-5">
          <SectionTitle title="裁判间 Cohen's kappa" desc="flash 裁判与 plus 裁判之间的一致性" />
          <div className="space-y-2">
            {kappa.map(([k, v]) => {
              const tone = kappaTone(v)
              return (
                <div key={k} className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 px-4 py-2.5">
                  <span className="min-w-0 truncate text-xs text-ink-700">{k}</span>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className={`rounded-md px-2 py-0.5 text-[11px] ${tone.bg} ${tone.text}`}>
                      {tone.label}
                    </span>
                    <span className="num w-14 text-right text-sm font-semibold text-ink-900">
                      {v.toFixed(3)}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
          <div className="mt-4 rounded-xl bg-slate-50/70 px-4 py-3 text-xs leading-relaxed text-ink-700">
            自一致率：{selfConsistency.map(([k, v]) => `${k} = ${v}`).join('，')}。kappa 全部贴着 0
            走，说明两个 LLM 裁判在同一批要点上基本各打各的。
          </div>
          <SourceNote>来源：results/v0.4-analysis.json 的 kappa 与 self_consistency 字段。</SourceNote>
        </Card>
      </div>

      <Card className="mt-6 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 px-5 pt-5">
          <SectionTitle title="人工裁定明细" desc="三裁判分歧项 + 标注人终裁，改判条目已标红" />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-sm">
            <thead>
              <tr className="border-y border-slate-200 bg-slate-50/80 text-left text-xs text-ink-500">
                <th className="px-4 py-2.5 font-medium">场景</th>
                <th className="px-4 py-2.5 font-medium">编号</th>
                <th className="px-3 py-2.5 text-center font-medium">规则</th>
                <th className="px-3 py-2.5 text-center font-medium">flash</th>
                <th className="px-3 py-2.5 text-center font-medium">plus</th>
                <th className="px-3 py-2.5 text-center font-medium">多数票</th>
                <th className="px-3 py-2.5 text-center font-medium">终裁</th>
                <th className="px-4 py-2.5 font-medium">要点 / 理由</th>
              </tr>
            </thead>
            <tbody>
              {adjudication.map((r, i) => (
                <Row key={`${r.场景}-${r.编号}-${i}`} row={r} />
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </PageWrap>
  )
}

function bit(v: number | string) {
  return v === 1 || v === '1' ? 1 : 0
}

function Row({ row }: { row: AdjudicationRow }) {
  const disputed = bit(row.多数票) !== bit(row.裁定)
  return (
    <tr className={`border-b border-slate-100 last:border-0 ${disputed ? 'bg-rose-50/50' : 'hover:bg-slate-50/60'}`}>
      <td className="num px-4 py-2.5 font-medium text-ink-900">{row.场景}</td>
      <td className="num px-4 py-2.5 text-ink-500">{row.编号}</td>
      {(['规则', 'flash', 'plus', '多数票'] as const).map((f) => (
        <td key={f} className="px-3 py-2.5 text-center">
          <span className={`num inline-block w-6 rounded ${bit(row[f]) ? 'bg-teal-50 text-teal-600' : 'bg-slate-100 text-ink-500'}`}>
            {bit(row[f])}
          </span>
        </td>
      ))}
      <td className="px-3 py-2.5 text-center">
        <span
          className={`num inline-block w-6 rounded font-semibold ${
            disputed ? 'bg-rose-100 text-rose-600' : 'bg-brand-soft text-brand'
          }`}
        >
          {bit(row.裁定)}
        </span>
      </td>
      <td className="max-w-[420px] px-4 py-2.5">
        <div className="truncate text-ink-700" title={row.要点}>
          {row.要点}
        </div>
        <div className="mt-0.5 line-clamp-2 text-xs text-ink-500">{row.理由}</div>
      </td>
    </tr>
  )
}
