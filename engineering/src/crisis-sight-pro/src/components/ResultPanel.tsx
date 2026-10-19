// 结果面板：四段式报告 + 风险徽章 + 导出 + 知识库命中来源

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  FileText,
  Copy,
  Download,
  Check,
  Library,
  ChevronDown,
  Target,
  Compass,
  ShieldAlert,
  CircleDot,
} from 'lucide-react'
import type { AnalysisResult, KbField } from '../engine/types'
import { buildMarkdown, copyText, downloadMarkdown } from '../lib/export'
import { GlassCard, Meter, RiskBadge, SectionTitle } from './ui'

const SECTIONS: { key: '态势概述' | '风险研判' | '分级行动建议' | '不确定性与盲点'; num: string; icon: typeof Target; accent: string }[] = [
  { key: '态势概述', num: '一', icon: Compass, accent: '#22d3ee' },
  { key: '风险研判', num: '二', icon: Target, accent: '#818cf8' },
  { key: '分级行动建议', num: '三', icon: CircleDot, accent: '#34d399' },
  { key: '不确定性与盲点', num: '四', icon: ShieldAlert, accent: '#fbbf24' },
]

const KB_FIELDS: { key: KbField; label: string; tone: string }[] = [
  { key: '特征', label: '特征', tone: '#22d3ee' },
  { key: '主要危害', label: '主要危害', tone: '#f472b6' },
  { key: '应对要点', label: '应对要点', tone: '#34d399' },
  { key: '次生灾害', label: '次生灾害', tone: '#fbbf24' },
  { key: '监测指标', label: '监测指标', tone: '#818cf8' },
]

export function ResultPanel({ result }: { result: AnalysisResult }) {
  const [copied, setCopied] = useState(false)
  const [kbOpen, setKbOpen] = useState(true)

  async function handleCopy() {
    const ok = await copyText(buildMarkdown(result))
    if (ok) {
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    }
  }

  return (
    <div className="space-y-5">
      {/* 报告头 */}
      <GlassCard className="overflow-hidden p-6 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="rounded-md border border-cyanline-500/30 bg-cyanline-500/10 px-2 py-0.5 text-[11px] text-cyanline-400">
                {result.input.disasterType}
              </span>
              <span className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[11px] text-slate-400">
                严重程度 {result.input.severity}
              </span>
              <span className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[11px] text-slate-400">
                命中知识库 {result.kbKey}
              </span>
            </div>
            <h2 className="text-xl font-bold text-slate-50">{result.report.title}</h2>
            <p className="mt-1.5 text-[13px] text-slate-400">{result.report.summary}</p>
          </div>

          <div className="flex flex-col items-start gap-3 sm:items-end">
            <RiskBadge level={result.riskLevel} score={result.riskScore} />
            <div className="w-48">
              <div className="mb-1 flex items-center justify-between text-[11px] text-slate-500">
                <span>研判置信度</span>
                <span className="tabnum">{result.confidence}%</span>
              </div>
              <Meter value={result.confidence} color="#818cf8" height={5} />
            </div>
          </div>
        </div>

        {/* 导出 */}
        <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-white/5 pt-4">
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-[13px] text-slate-200 transition-all hover:border-cyanline-500/40 hover:text-white"
          >
            {copied ? (
              <Check className="h-4 w-4 text-emerald-400" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
            {copied ? '已复制' : '复制报告'}
          </button>
          <button
            onClick={() => downloadMarkdown(result)}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-[13px] text-slate-200 transition-all hover:border-indigoink-500/40 hover:text-white"
          >
            <Download className="h-4 w-4" />
            下载 Markdown
          </button>
          <span className="ml-auto inline-flex items-center gap-1.5 text-[11px] text-slate-500">
            <FileText className="h-3.5 w-3.5" />
            生成于 {new Date(result.createdAt).toLocaleString('zh-CN')}
          </span>
        </div>
      </GlassCard>

      {/* 四段式报告 */}
      <div className="grid gap-5 lg:grid-cols-2">
        {SECTIONS.map((s, i) => (
          <motion.div
            key={s.key}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: i * 0.08 }}
          >
            <GlassCard className="lift h-full p-5">
              <SectionTitle icon={<s.icon className="h-4 w-4" />} title={`${s.num}、${s.key}`} accent={s.accent} />
              <p className="mt-3 whitespace-pre-line text-[13.5px] leading-[1.9] text-slate-300">
                {result.report[s.key]}
              </p>
            </GlassCard>
          </motion.div>
        ))}
      </div>

      {/* 知识库命中来源 */}
      <GlassCard className="p-5">
        <button
          onClick={() => setKbOpen((v) => !v)}
          className="flex w-full items-center justify-between gap-4 text-left"
        >
          <SectionTitle
            icon={<Library className="h-4 w-4" />}
            title="知识库命中来源"
            desc={`本次推演命中的条目「${result.kbKey}」，四个智能体的发言均从中取材。`}
            accent="#fbbf24"
          />
          <ChevronDown
            className={`h-4 w-4 shrink-0 text-slate-500 transition-transform ${
              kbOpen ? 'rotate-180' : ''
            }`}
          />
        </button>

        {kbOpen && (
          <div className="mt-4 grid gap-3 border-t border-white/5 pt-4 sm:grid-cols-2">
            {KB_FIELDS.map((f) => (
              <div
                key={f.key}
                className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4"
              >
                <div className="mb-1.5 flex items-center gap-2">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: f.tone }}
                  />
                  <span className="text-[12.5px] font-semibold" style={{ color: f.tone }}>
                    {f.label}
                  </span>
                  {result.kbRefs.includes(f.key) && (
                    <span className="ml-auto rounded bg-white/[0.06] px-1.5 py-0.5 text-[10px] text-slate-400">
                      被引用
                    </span>
                  )}
                </div>
                <p className="text-[12.5px] leading-relaxed text-slate-400">
                  {result.kbEntry[f.key]}
                </p>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  )
}
