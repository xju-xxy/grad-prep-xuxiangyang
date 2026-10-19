// 打字机效果。按固定节奏往外吐字，吐完把 done 置真，
// 父组件据此推进流水线到下一段发言。

import { useEffect, useState } from 'react'

export function useTypewriter(text: string, enabled: boolean, cps = 120) {
  const [count, setCount] = useState(enabled ? 0 : text.length)

  useEffect(() => {
    if (!enabled) {
      setCount(text.length)
      return
    }
    setCount(0)
    if (!text) return

    const interval = 1000 / 60
    const perTick = Math.max(1, Math.round(cps / 60))
    let i = 0
    let timer = 0

    const tick = () => {
      i += perTick
      if (i >= text.length) {
        setCount(text.length)
        return
      }
      setCount(i)
      timer = window.setTimeout(tick, interval)
    }
    timer = window.setTimeout(tick, interval)
    return () => window.clearTimeout(timer)
  }, [text, enabled, cps])

  return { shown: text.slice(0, count), done: count >= text.length }
}
