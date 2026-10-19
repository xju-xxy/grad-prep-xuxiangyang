import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X, ZoomIn } from 'lucide-react'
import { Card, PageWrap, SectionTitle, SourceNote } from '../components/ui'

const FIGURES = [
  { file: 'fig1_radar.png', title: '三层得分雷达', note: '各配置在事实 / 推理 / 决策层的对比雷达。' },
  { file: 'fig2_heatmap.png', title: '场景 × 配置热力图', note: '36 个场景逐场景的得分热力分布。' },
  { file: 'fig3_kappa_matrix.png', title: '裁判 kappa 矩阵', note: 'flash 与 plus 裁判之间的一致性矩阵。' },
  { file: 'fig4_hardpoints.png', title: '难点失分', note: '容易丢分的要点类型分布。' },
  { file: 'fig5_cost.png', title: '成本对比', note: '各配置的 token / 调用消耗。' },
]

export default function FigureGallery() {
  const [zoom, setZoom] = useState<string | null>(null)
  const url = (f: string) => `${import.meta.env.BASE_URL}figures/${f}`

  return (
    <PageWrap>
      <SectionTitle
        title="图表库"
        desc="实验跑完时顺手出的几张图，原图放在 research/crisis-bench/figures，这里直接引过来"
      />

      <div className="grid gap-5 sm:grid-cols-2">
        {FIGURES.map((f) => (
          <Card key={f.file} hover className="overflow-hidden">
            <button
              onClick={() => setZoom(f.file)}
              className="group relative block w-full bg-slate-50"
            >
              <img src={url(f.file)} alt={f.title} className="h-56 w-full object-contain p-3" />
              <span className="absolute right-3 top-3 flex items-center gap-1 rounded-lg bg-white/90 px-2 py-1 text-[11px] font-medium text-ink-700 opacity-0 shadow-card transition-opacity group-hover:opacity-100">
                <ZoomIn size={13} /> 放大
              </span>
            </button>
            <div className="px-4 pb-4">
              <div className="text-sm font-semibold text-ink-900">{f.title}</div>
              <div className="mt-1 text-xs text-ink-500">{f.note}</div>
              <div className="mt-1 text-[11px] text-ink-300">figures/{f.file}</div>
            </div>
          </Card>
        ))}
      </div>

      <SourceNote>来源：research/crisis-bench/figures/*.png（原样复制到 public/figures）。</SourceNote>

      <AnimatePresence>
        {zoom && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setZoom(null)}
            className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/70 p-6 backdrop-blur-sm"
          >
            <motion.img
              initial={{ scale: 0.96 }}
              animate={{ scale: 1 }}
              src={url(zoom)}
              alt={zoom}
              className="max-h-[88vh] max-w-[92vw] rounded-2xl bg-white object-contain p-3 shadow-2xl"
            />
            <button
              onClick={() => setZoom(null)}
              className="absolute right-6 top-6 rounded-xl bg-white/90 p-2 text-ink-700 shadow-card hover:bg-white"
            >
              <X size={20} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </PageWrap>
  )
}
