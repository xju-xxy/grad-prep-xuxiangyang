// 报告的导出：拼 Markdown、复制到剪贴板、下载 .md 文件。

import type { AnalysisResult } from '../engine/types'
import { AGENT_ORDER } from '../engine/agents'

export function buildMarkdown(result: AnalysisResult): string {
  const { report, input, kbEntry, kbKey, riskLevel, riskScore } = result
  const lines: string[] = []

  lines.push(`# ${report.title}`)
  lines.push('')
  lines.push(`> ${report.summary}`)
  lines.push('')
  lines.push('## 一、态势概述')
  lines.push('')
  lines.push(report.态势概述)
  lines.push('')
  lines.push('## 二、风险研判')
  lines.push('')
  lines.push(report.风险研判)
  lines.push('')
  lines.push('## 三、分级行动建议')
  lines.push('')
  lines.push(report.分级行动建议)
  lines.push('')
  lines.push('## 四、不确定性与盲点')
  lines.push('')
  lines.push(report.不确定性与盲点)
  lines.push('')

  lines.push('---')
  lines.push('')
  lines.push('## 推演经过（四个智能体 × 两轮）')
  lines.push('')
  for (const round of [1, 2]) {
    lines.push(`### 第 ${round} 轮`)
    lines.push('')
    for (const agent of AGENT_ORDER) {
      const msg = result.messages.find((m) => m.agent === agent && m.round === round)
      if (!msg) continue
      lines.push(`**${agent}**（引用知识库：${msg.kbRefs.join('、') || '无'}）`)
      lines.push('')
      lines.push(msg.content)
      lines.push('')
    }
  }

  lines.push('---')
  lines.push('')
  lines.push('## 知识库命中来源')
  lines.push('')
  lines.push(`- 命中条目：${kbKey}`)
  lines.push(`- 特征：${kbEntry.特征}`)
  lines.push(`- 主要危害：${kbEntry.主要危害}`)
  lines.push(`- 应对要点：${kbEntry.应对要点}`)
  lines.push(`- 次生灾害：${kbEntry.次生灾害}`)
  lines.push(`- 监测指标：${kbEntry.监测指标}`)
  lines.push('')
  lines.push(
    `- 输入：${input.disasterType}｜${input.severity}｜${input.location || '未填地点'}｜${
      input.timeHint || '未填时间'
    }`,
  )
  lines.push(`- 风险等级：${riskLevel}（${riskScore}/100）`)
  lines.push('')
  lines.push(`_生成时间：${new Date(result.createdAt).toLocaleString('zh-CN')}_`)
  lines.push('')

  return lines.join('\n')
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // 剪贴板 API 在非安全上下文下会失败，退回老办法
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      return ok
    } catch {
      return false
    }
  }
}

export function downloadMarkdown(result: AnalysisResult): void {
  const md = buildMarkdown(result)
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const stamp = new Date(result.createdAt)
    .toISOString()
    .slice(0, 19)
    .replace(/[:T]/g, '-')
  const a = document.createElement('a')
  a.href = url
  a.download = `crisis-report-${result.input.disasterType}-${stamp}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
