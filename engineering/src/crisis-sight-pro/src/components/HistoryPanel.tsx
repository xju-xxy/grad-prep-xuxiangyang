// 推演记录抽屉。数据来自 localStorage，点一条就把那次结果还原出来。

import { AnimatePresence, motion } from 'framer-motion'
import { History, Trash2, X, Clock3 } from 'lucide-react'
import type { HistoryRecord } from '../lib/history'
import { RiskBadge } from './ui'

export function HistoryPanel({
  open,
  records,
  onPick,
  onClear,
  onClose,
}: {
  open: boolean
  records: HistoryRecord[]
  onPick: (r: HistoryRecord) => void
  onClear: () => void
  onClose: () => void
}) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-abyss-900/60 backdrop-blur-sm"
          />
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 26, stiffness: 240 }}
            className="glass fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col rounded-l-2xl"
          >
            <div className="flex items-center justify-between border-b border-white/[0.08] px-5 py-4">
              <div className="flex items-center gap-2.5">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyanline-500/12 text-cyanline-500">
                  <History className="h-4 w-4" />
                </span>
                <div>
                  <div className="text-[14px] font-semibold text-slate-100">推演记录</div>
                  <div className="text-[11px] text-slate-500">
                    本地保存最近 {records.length} 次
                  </div>
                </div>
              </div>
              <button
                onClick={onClose}
                className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-white/5 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto p-5">
              {records.length === 0 && (
                <div className="mt-16 text-center text-[13px] text-slate-500">
                  还没有记录，跑一次推演就会留在这里
                </div>
              )}
              {records.map((r) => (
                <button
                  key={r.id}
                  onClick={() => onPick(r)}
                  className="lift w-full rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 text-left"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-[13px] font-semibold text-slate-100">
                      {r.disasterType}
                      <span className="ml-2 text-[11px] font-normal text-slate-500">
                        {r.severity}
                      </span>
                    </span>
                    <RiskBadge level={r.riskLevel} compact />
                  </div>
                  <p className="mt-1.5 line-clamp-2 text-[12.5px] leading-relaxed text-slate-400">
                    {r.sceneBrief}
                  </p>
                  <div className="mt-2 flex items-center gap-1.5 text-[11px] text-slate-500">
                    <Clock3 className="h-3 w-3" />
                    {new Date(r.createdAt).toLocaleString('zh-CN')}
                  </div>
                </button>
              ))}
            </div>

            {records.length > 0 && (
              <div className="border-t border-white/[0.08] p-4">
                <button
                  onClick={onClear}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] py-2.5 text-[13px] text-slate-300 transition-colors hover:border-red-500/40 hover:text-red-300"
                >
                  <Trash2 className="h-4 w-4" />
                  清空全部记录
                </button>
              </div>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
