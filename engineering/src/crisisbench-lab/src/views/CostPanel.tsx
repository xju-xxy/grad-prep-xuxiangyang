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
import type { Dataset } from '../types'
import { sortedConfigs } from '../lib/data'
import { meta } from '../lib/theme'
import { compact } from '../lib/format'
import { Card, PageWrap, SectionTitle, SourceNote, StatCard } from '../components/ui'

const fmtTokens = (n: number) => n.toLocaleString('en-US')

function fmtDuration(sec: number) {
  const h = sec / 3600
  if (h >= 1) return `${h.toFixed(1)} 小时`
  return `${Math.round(sec / 60)} 分钟`
}

export default function CostPanel({ data }: { data: Dataset }) {
  const { analysis, cost } = data
  const keys = sortedConfigs(analysis)
  const rows = keys
    .map((k) => ({ k, row: cost.rows.find((r) => r.配置 === k)! }))
    .filter((x) => x.row)

  const totalCalls = rows.reduce((n, x) => n + x.row.协议合计.调用数, 0)
  const totalTokens = rows.reduce((n, x) => n + x.row.协议合计.total, 0)
  const totalSec = rows.reduce((n, x) => n + x.row.协议合计.耗时秒, 0)
  const perScene = totalTokens / (36 * rows.length)

  const tokenData = rows
    .map((x) => ({ name: meta(x.k).short, tokens: x.row.协议合计.total, fill: meta(x.k).color }))
    .sort((a, b) => b.tokens - a.tokens)

  const callData = rows.map((x) => ({
    name: meta(x.k).short,
    calls: x.row.协议合计.调用数,
    fill: meta(x.k).color,
  }))

  return (
    <PageWrap>
      <SectionTitle
        title="成本"
        desc="每个配置跑 36 个场景花了多少次调用、多少 token、多少时间"
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="协议总调用" value={totalCalls.toLocaleString('en-US')} unit="次" hint="六组配置合计" />
        <StatCard label="协议总 token" value={compact(totalTokens)} unit="tokens" hint="prompt + completion" tone="teal" />
        <StatCard label="总耗时" value={fmtDuration(totalSec)} hint="wall-clock 累计" tone="amber" />
        <StatCard label="单场景均 token" value={Math.round(perScene).toLocaleString('en-US')} hint="按 36 场景 × 6 配置" tone="pink" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <SectionTitle title="协议 token 消耗" desc="主运行 + plus 裁判重打分 + 自一致 的合计" />
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={tokenData} layout="vertical" margin={{ left: 8, right: 56, top: 4, bottom: 4 }}>
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={92}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 12, fill: '#334155' }}
                />
                <Tooltip
                  cursor={{ fill: 'rgba(79,70,229,0.06)' }}
                  formatter={(v: number) => [fmtTokens(v), 'token']}
                />
                <Bar dataKey="tokens" radius={[0, 6, 6, 0]} barSize={20}>
                  {tokenData.map((d) => (
                    <Cell key={d.name} fill={d.fill} />
                  ))}
                  <LabelList
                    dataKey="tokens"
                    position="right"
                    formatter={(v: number) => compact(v)}
                    style={{ fontSize: 12, fill: '#334155', fontVariantNumeric: 'tabular-nums' }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-5">
          <SectionTitle title="协议调用次数" />
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={callData} layout="vertical" margin={{ left: 8, right: 44, top: 4, bottom: 4 }}>
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={92}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 12, fill: '#334155' }}
                />
                <Tooltip cursor={{ fill: 'rgba(79,70,229,0.06)' }} formatter={(v: number) => [`${v} 次`, '调用']} />
                <Bar dataKey="calls" radius={[0, 6, 6, 0]} barSize={20}>
                  {callData.map((d) => (
                    <Cell key={d.name} fill={d.fill} />
                  ))}
                  <LabelList
                    dataKey="calls"
                    position="right"
                    style={{ fontSize: 12, fill: '#334155', fontVariantNumeric: 'tabular-nums' }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card className="mt-6 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80 text-left text-xs text-ink-500">
                <th className="px-4 py-3 font-medium">配置</th>
                <th className="px-4 py-3 font-medium">被测模型</th>
                <th className="px-4 py-3 text-right font-medium">调用数</th>
                <th className="px-4 py-3 text-right font-medium">prompt</th>
                <th className="px-4 py-3 text-right font-medium">completion</th>
                <th className="px-4 py-3 text-right font-medium">total token</th>
                <th className="px-4 py-3 text-right font-medium">耗时</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ k, row }) => (
                <tr key={k} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/60">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: meta(k).color }} />
                      <span className="font-medium text-ink-900">{meta(k).short}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-ink-700">{row.被测模型}</td>
                  <td className="num px-4 py-3 text-right text-ink-700">{row.协议合计.调用数}</td>
                  <td className="num px-4 py-3 text-right text-ink-700">{fmtTokens(row.协议合计.prompt)}</td>
                  <td className="num px-4 py-3 text-right text-ink-700">{fmtTokens(row.协议合计.completion)}</td>
                  <td className="num px-4 py-3 text-right font-semibold text-ink-900">{fmtTokens(row.协议合计.total)}</td>
                  <td className="num px-4 py-3 text-right text-ink-700">{fmtDuration(row.协议合计.耗时秒)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-slate-100 px-4 py-3 text-xs text-ink-500">
          single@glm-4-flash 的推演是「同提示词独立实测」，多出一次 flash 裁判自一致复跑，明细见源文件。
        </div>
      </Card>

      <Card className="mt-6 p-5">
        <SectionTitle title="费用说明" />
        <p className="text-sm leading-relaxed text-ink-700">
          cost-summary.json 里只有调用次数、token 和耗时，没有金额字段，所以这里不折算成钱。
          想估预算的话，拿上表的 total token 乘对应模型的单价即可。
        </p>
        <SourceNote>来源：results/cost-summary.json 的 协议合计 字段。</SourceNote>
      </Card>
    </PageWrap>
  )
}
