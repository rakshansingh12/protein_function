export function fmt(n: number, maxDecimals = 4): string {
  return n.toLocaleString('en-US', { maximumFractionDigits: maxDecimals })
}

export function pct(fraction: number, maxDecimals = 2): string {
  return `${(fraction * 100).toLocaleString('en-US', { maximumFractionDigits: maxDecimals })}%`
}

export function decimalsOf(n: number): number {
  const s = String(n)
  const i = s.indexOf('.')
  return i === -1 ? 0 : Math.min(4, s.length - i - 1)
}

export const uniprotUrl = (accession: string) => `https://www.uniprot.org/uniprotkb/${accession}`
