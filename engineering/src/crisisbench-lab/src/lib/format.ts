export const pct = (n: number, digits = 1) => `${n.toFixed(digits)}%`

/** 带符号的百分点，例如 -7.20pp / +7.04pp */
export const pp = (n: number, digits = 2) =>
  `${n > 0 ? '+' : ''}${n.toFixed(digits)}pp`

export const compact = (n: number) =>
  n >= 10000 ? `${(n / 1000).toFixed(1)}k` : n.toLocaleString('en-US')

/** 把 p 值写成 1.85×10⁻⁹ 这种好读的形式 */
export function sci(p: number | null | undefined): string {
  if (p === null || p === undefined) return '—'
  if (p === 0) return '< 1×10⁻¹⁶'
  if (p >= 0.001) return p.toFixed(4).replace(/0+$/, '').replace(/\.$/, '')
  const [m, e] = p.toExponential(2).split('e')
  const sup: Record<string, string> = {
    '-': '⁻',
    '0': '⁰',
    '1': '¹',
    '2': '²',
    '3': '³',
    '4': '⁴',
    '5': '⁵',
    '6': '⁶',
    '7': '⁷',
    '8': '⁸',
    '9': '⁹',
  }
  const exp = e
    .split('')
    .map((c) => sup[c] ?? c)
    .join('')
  return `${m}×10${exp}`
}
