// 首页输入台：灾情描述 + 灾害类型 + 严重程度 + 地点/时间，外加四个预置场景

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  ClipboardList,
  CornerDownRight,
  MapPin,
  Play,
  RotateCcw,
  Sparkles,
  Clock3,
} from 'lucide-react'
import type { DisasterType, InputPayload, Severity } from '../engine/types'
import { DISASTER_TYPES } from '../engine/knowledgeBase'
import { PRESETS } from '../engine/examples'
import { GlassCard, SectionTitle } from './ui'

const SEVERITIES: Severity[] = ['轻微', '一般', '严重', '特重']

export function InputConsole({
  onStart,
  onPickHistory,
}: {
  onStart: (input: InputPayload) => void
  onPickHistory: () => void
}) {
  const [scene, setScene] = useState(PRESETS[0].scene)
  const [disasterType, setDisasterType] = useState<DisasterType>('地震')
  const [severity, setSeverity] = useState<Severity>('严重')
  const [location, setLocation] = useState(PRESETS[0].location)
  const [timeHint, setTimeHint] = useState(PRESETS[0].timeHint)

  const canStart = scene.trim().length >= 6

  function applyPreset(id: string) {
    const p = PRESETS.find((x) => x.id === id)
    if (!p) return
    setScene(p.scene)
    setDisasterType(p.disasterType)
    setSeverity(p.severity)
    setLocation(p.location)
    setTimeHint(p.timeHint)
  }

  function reset() {
    setScene('')
    setLocation('')
    setTimeHint('')
    setDisasterType('地震')
    setSeverity('一般')
  }

  return (
    <GlassCard className="p-6 sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <SectionTitle
          icon={<ClipboardList className="h-4 w-4" />}
          title="灾情输入台"
          desc="把现场情况写清楚，选好灾种，引擎会带着灾害知识库跑一遍推演。"
        />
        <button
          onClick={onPickHistory}
          className="text-xs text-slate-400 transition-colors hover:text-cyanline-400"
        >
          查看历史推演 →
        </button>
      </div>

      {/* 预置场景 */}
      <div className="mt-6">
        <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-500">
          <Sparkles className="h-3.5 w-3.5" />
          预置场景 · 一键填充
        </div>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => {
            const active = p.scene === scene
            return (
              <button
                key={p.id}
                onClick={() => applyPreset(p.id)}
                className={`group rounded-xl border px-3.5 py-2 text-left transition-all ${
                  active
                    ? 'border-cyanline-500/50 bg-cyanline-500/10'
                    : 'border-white/10 bg-white/[0.03] hover:border-cyanline-500/30 hover:bg-white/[0.06]'
                }`}
              >
                <div
                  className={`text-[13px] font-semibold ${
                    active ? 'text-cyanline-400' : 'text-slate-200'
                  }`}
                >
                  {p.label}
                </div>
                <div className="text-[11px] text-slate-500">{p.hint}</div>
              </button>
            )
          })}
        </div>
      </div>

      {/* 灾情描述 */}
      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between">
          <label className="text-[13px] font-medium text-slate-300">灾情描述</label>
          <span className="tabnum text-[11px] text-slate-500">{scene.length} 字</span>
        </div>
        <textarea
          value={scene}
          onChange={(e) => setScene(e.target.value)}
          rows={5}
          placeholder="例如：凌晨山区发生地震，多处房屋倒塌，道路中断，有人员被埋压……"
          className="w-full resize-y rounded-xl border border-white/10 bg-abyss-900/60 p-4 text-[14px] leading-relaxed text-slate-100 placeholder:text-slate-600 transition-colors focus:border-cyanline-500/50 focus:ring-2 focus:ring-cyanline-500/20"
        />
      </div>

      {/* 灾害类型 */}
      <div className="mt-5">
        <label className="mb-2 block text-[13px] font-medium text-slate-300">
          灾害类型
        </label>
        <div className="flex flex-wrap gap-2">
          {DISASTER_TYPES.map((t) => {
            const active = t === disasterType
            return (
              <button
                key={t}
                onClick={() => setDisasterType(t)}
                className={`rounded-lg border px-3 py-1.5 text-[12.5px] transition-all ${
                  active
                    ? 'border-cyanline-500/60 bg-cyanline-500/15 font-semibold text-cyanline-400 shadow-glow'
                    : 'border-white/10 bg-white/[0.03] text-slate-300 hover:border-white/25 hover:text-white'
                }`}
              >
                {t}
              </button>
            )
          })}
        </div>
      </div>

      {/* 严重程度 + 地点 + 时间 */}
      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <div className="sm:col-span-1">
          <label className="mb-2 block text-[13px] font-medium text-slate-300">
            严重程度
          </label>
          <div className="flex overflow-hidden rounded-xl border border-white/10 bg-abyss-900/50 p-1">
            {SEVERITIES.map((s) => {
              const active = s === severity
              const tone =
                s === '特重' ? '#ef4444' : s === '严重' ? '#f59e0b' : s === '一般' ? '#22d3ee' : '#34d399'
              return (
                <button
                  key={s}
                  onClick={() => setSeverity(s)}
                  className={`flex-1 rounded-lg py-1.5 text-[12.5px] transition-all ${
                    active ? 'font-semibold text-abyss-900' : 'text-slate-400 hover:text-slate-200'
                  }`}
                  style={active ? { background: tone } : undefined}
                >
                  {s}
                </button>
              )
            })}
          </div>
        </div>

        <div>
          <label className="mb-2 flex items-center gap-1.5 text-[13px] font-medium text-slate-300">
            <MapPin className="h-3.5 w-3.5 text-slate-500" />
            发生地点（选填）
          </label>
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="如：某县城老城区"
            className="w-full rounded-xl border border-white/10 bg-abyss-900/60 px-3.5 py-2.5 text-[13.5px] text-slate-100 placeholder:text-slate-600 focus:border-cyanline-500/50 focus:ring-2 focus:ring-cyanline-500/20"
          />
        </div>

        <div>
          <label className="mb-2 flex items-center gap-1.5 text-[13px] font-medium text-slate-300">
            <Clock3 className="h-3.5 w-3.5 text-slate-500" />
            时间（选填）
          </label>
          <input
            value={timeHint}
            onChange={(e) => setTimeHint(e.target.value)}
            placeholder="如：今日凌晨 03:00"
            className="w-full rounded-xl border border-white/10 bg-abyss-900/60 px-3.5 py-2.5 text-[13.5px] text-slate-100 placeholder:text-slate-600 focus:border-cyanline-500/50 focus:ring-2 focus:ring-cyanline-500/20"
          />
        </div>
      </div>

      {/* 操作区 */}
      <div className="mt-7 flex flex-wrap items-center gap-3">
        <motion.button
          whileHover={{ y: -2 }}
          whileTap={{ scale: 0.98 }}
          disabled={!canStart}
          onClick={() =>
            onStart({ scene, disasterType, severity, location, timeHint })
          }
          className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyanline-500 to-indigoink-500 px-6 py-3 text-[14px] font-semibold text-abyss-900 shadow-glow transition-all disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Play className="h-4 w-4 fill-current" />
          开始推演
          <CornerDownRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </motion.button>

        <button
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-[13.5px] text-slate-300 transition-all hover:border-white/25 hover:text-white"
        >
          <RotateCcw className="h-4 w-4" />
          清空
        </button>

        {!canStart && (
          <span className="text-xs text-slate-500">灾情描述至少写几个字</span>
        )}
      </div>
    </GlassCard>
  )
}
