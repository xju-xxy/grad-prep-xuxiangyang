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
import { configScore, sortedConfigs } from '../lib/data'
import { meta } from '../lib/theme'
import { pct, pp, sci } from '../lib/format'
import { Card, PageWrap, SectionTitle, SourceNote, StatCard } from '../components/ui'

export default function Overview({ data }: { data: Dataset }) {
  const { analysis, scenarios } = data
  const keys = sortedConfigs(analysis)

  const pointTotal = scenarios.scenarios.reduce(
    (n, s) => n + s.rubric.事实层.length + s.rubric.推理层.length + s.rubric.决策层.length,
    0,
  )

  const ranked = keys
    .map((k) => ({ key: k, ...configScore(analysis, k), m: meta(k) }))
    .sort((a, b) => b.overall.score - a.overall.score)

  const best = ranked[0]
  const worst = ranked[ranked.length - 1]

  const rq = analysis.tests
  const rqRows = [
    {
      id: 'RQ1',
      title: 'multi vs single',
      pair: rq['RQ1: multi vs single'],
      tone: 'brand' as const,
    },
    {
      id: 'RQ2',
      title: 'noaudit vs multi（去掉审核官）',
      pair: rq['RQ2: noaudit vs multi'],
      tone: 'amber' as const,
    },
    {
      id: 'RQ4',
      title: 'verify vs multi（接 Verifier）',
      pair: rq['RQ4: verify vs multi'],
      tone: 'pink' as const,
    },
    {
      id: 'A2',
      title: 'plus vs flash（换模型档位）',
      pair: rq['A2: 被测模型 plus vs flash'],
      tone: 'teal' as const,
    },
  ]

  return (
    <PageWrap>
      <header className="mb-8">
        <div className="inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand-soft px-3 py-1 text-xs font-medium text-brand">
          论文项目 · 真实实验结果看板
        </div>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-ink-900 sm:text-4xl">
          把 CrisisBench 的评测结果摊开看
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-ink-700">
          CrisisBench 是我做的多智能体灾害态势推理评测基准：36 个中文灾害场景，每个场景按
          「事实层 / 推理层 / 决策层」三层给分，用三裁判多数票（规则 + glm-4-flash + glm-4-plus
          2-of-3）当口径。这个看板把 v0.4 全量实验的结果从 JSON 里摊出来，方便对着数字看结论。
        </p>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-500">
          <span>数据生成时间：{analysis.meta.时间}</span>
          <span>口径：三裁判多数票</span>
          <span>来源：research/crisis-bench/results</span>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="评测场景" value={scenarios.scenarios.length} unit="个" hint="v0.4 扩容版" />
        <StatCard label="对比配置" value={keys.length} unit="组" hint="含消融与对照" />
        <StatCard label="三层评测要点" value={pointTotal} unit="条" hint="事实 + 推理 + 决策" tone="teal" />
        <StatCard
          label="得分区间"
          value={pct(worst.overall.score) + ' – ' + pct(best.overall.score)}
          hint="六组配置的三层加权总分"
          tone="slate"
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <SectionTitle
            title="研究问题速览"
            desc="场景级均值差 = 后者 − 前者（负数就是后者更低）；正负只是方向，好坏看下面的解读"
          />
          <div className="space-y-3">
            {rqRows.map((r) => {
              const diff = r.pair?.mean_diff_pp ?? 0
              const up = diff >= 0
              return (
                <div
                  key={r.id}
                  className="flex items-center justify-between gap-4 rounded-xl border border-slate-100 bg-slate-50/60 px-4 py-3"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="rounded-md bg-white px-1.5 py-0.5 text-[11px] font-semibold text-ink-500 ring-1 ring-slate-200">
                        {r.id}
                      </span>
                      <span className="truncate text-sm font-medium text-ink-900">{r.title}</span>
                    </div>
                    <div className="mt-1 text-xs text-ink-500">
                      McNemar p = {sci(r.pair?.mcnemar?.p as number)} · Wilcoxon p ={' '}
                      {sci(r.pair?.wilcoxon?.p as number)}
                    </div>
                  </div>
                  <div className="num shrink-0 text-right text-lg font-semibold text-ink-900">
                    {pp(diff)}
                    <div className="text-[11px] font-normal text-ink-500">
                      {up ? '后者更高' : '后者更低'}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
          <SourceNote>来源：results/v0.4-analysis.json 的 tests 字段。</SourceNote>
        </Card>

        <Card className="p-5">
          <SectionTitle title="四组主配置的三层总分" desc="每根柱是一个配置的加权总分（命中要点 / 总要点）" />
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={ranked.map((r) => ({
                  name: r.m.short,
                  score: Number(r.overall.score.toFixed(1)),
                  fill: r.m.color,
                }))}
                layout="vertical"
                margin={{ left: 8, right: 40, top: 4, bottom: 4 }}
              >
                <XAxis type="number" domain={[0, 100]} hide />
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
                  formatter={(v: number) => [`${v}%`, '总分']}
                />
                <Bar dataKey="score" radius={[0, 6, 6, 0]} barSize={18}>
                  {ranked.map((r) => (
                    <Cell key={r.key} fill={r.m.color} />
                  ))}
                  <LabelList
                    dataKey="score"
                    position="right"
                    formatter={(v: number) => `${v}%`}
                    style={{ fontSize: 12, fill: '#334155', fontVariantNumeric: 'tabular-nums' }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <SourceNote>
            来源：results/v0.4-analysis.json 各 config 的 matrix 逐场景累加；与 RESULTS-v0.4.md
            的逐场景综合分可对上。
          </SourceNote>
        </Card>
      </div>

      <Card className="mt-6 p-5">
        <SectionTitle title="读之前先知道这几点" />
        <ul className="grid gap-2.5 text-sm leading-relaxed text-ink-700 sm:grid-cols-2">
          <li className="rounded-xl bg-slate-50/70 px-4 py-3">
            RQ1：multi@flash 比 single@flash 高 7.2pp（p&lt;1e-8，自助法 CI 不含 0），多智能体编排在多数票口径下确实赢了单模型直出。
          </li>
          <li className="rounded-xl bg-slate-50/70 px-4 py-3">
            RQ2：去掉审核官的 noaudit 比 multi 低 7.04pp，说明审核官这一环是在贡献分的，不是摆设。
          </li>
          <li className="rounded-xl bg-slate-50/70 px-4 py-3">
            RQ4：接上 Verifier 的 multi-verify 比 multi 再高 2.81pp，是三组消融里最好的一个配置。
          </li>
          <li className="rounded-xl bg-slate-50/70 px-4 py-3">
            三裁判之间的 kappa 都在 0.1 以下（最好的 0.081），单个裁判基本不可信，分数全靠三裁判多数票兜底。
          </li>
          <li className="rounded-xl bg-slate-50/70 px-4 py-3">
            glm-4-plus 整体比 flash 高 9.39pp，但它在 multi 下已经刷到接近满分（36 个场景里 35 个 100%），天花板效应明显，别再往上堆模型档位了。
          </li>
          <li className="rounded-xl bg-slate-50/70 px-4 py-3">
            失分点最集中的是「数值推算失败」：flash 三组配置各丢 27-39 个要点，是拉不开分的真正瓶颈。
          </li>
        </ul>
        <SourceNote>
          以上结论对应的数字都能在 results/v0.4-analysis.json 的 tests 与 kappa 字段里查到。
        </SourceNote>
      </Card>
    </PageWrap>
  )
}
