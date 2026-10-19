// 把 research/crisis-bench 下的真实结果文件裁剪/复制到 public/。
// 用法：node scripts/prepare-data.mjs   （在 crisisbench-lab 目录下跑）
import { readFileSync, writeFileSync, mkdirSync, copyFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '..')                       // crisisbench-lab/
const repo = resolve(root, '../../..')                 // 仓库根
const src = join(repo, 'research', 'crisis-bench')
const outData = join(root, 'public', 'data')
const outFig = join(root, 'public', 'figures')
mkdirSync(outData, { recursive: true })
mkdirSync(outFig, { recursive: true })

const read = (p) => JSON.parse(readFileSync(join(src, p), 'utf8'))

// 1) 直接搬运的结果文件
writeFileSync(join(outData, 'analysis.json'), JSON.stringify(read('results/v0.4-analysis.json')))
writeFileSync(join(outData, 'cost-summary.json'), JSON.stringify(read('results/cost-summary.json')))
writeFileSync(join(outData, 'adjudication.json'), JSON.stringify(read('results/adjudication.json')))

// 2) scenarios.json 太大（含 match 关键词表），只留页面要用的字段
const sc = read('scenarios/scenarios.json')
const slim = {
  meta: sc.meta,
  scenarios: sc.scenarios.map((s) => ({
    id: s.id,
    category: s['类别'],
    disaster: s['灾种'],
    timePoint: s['时间点'],
    intel: s['情报'],
    resources: s['资源'],
    rubric: {
      事实层: (s.rubric['事实层'] || []).map((r) => ({ point: r['要点'] })),
      推理层: (s.rubric['推理层'] || []).map((r) => ({
        point: r['要点'],
        from: r['起点'],
        mech: r['机制'],
        to: r['终点'],
      })),
      决策层: (s.rubric['决策层'] || []).map((r) => ({ point: r['要点'] })),
    },
  })),
}
writeFileSync(join(outData, 'scenarios.json'), JSON.stringify(slim))

// 3) 图
for (const f of ['fig1_radar.png', 'fig2_heatmap.png', 'fig3_kappa_matrix.png', 'fig4_hardpoints.png', 'fig5_cost.png']) {
  if (existsSync(join(src, 'figures', f))) copyFileSync(join(src, 'figures', f), join(outFig, f))
}

console.log('done. scenarios:', slim.scenarios.length, 'configs:', Object.keys(read('results/v0.4-analysis.json').configs).length)
