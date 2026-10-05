export const STANDARD_AA = 'ACDEFGHIKLMNPQRSTVWY'
export const MIN_RESIDUES = 50
export const MAX_CHARS = 20000

export function cleanSequence(raw: string): string {
  return raw
    .split(/\r?\n/)
    .filter((line) => !line.trim().startsWith('>'))
    .join('')
    .replace(/\s+/g, '')
    .toUpperCase()
}

export interface SequenceValidation {
  cleaned: string
  length: number
  invalidChars: string[]
  tooShort: boolean
  tooLong: boolean
  ok: boolean
}

export function validateSequence(raw: string): SequenceValidation {
  const cleaned = cleanSequence(raw)
  const invalidChars = Array.from(new Set(cleaned.replace(/[ACDEFGHIKLMNPQRSTVWY]/g, '').split(''))).filter(Boolean)
  const tooLong = raw.length > MAX_CHARS
  const tooShort = cleaned.length < MIN_RESIDUES
  return {
    cleaned,
    length: cleaned.length,
    invalidChars,
    tooShort,
    tooLong,
    ok: !tooLong && !tooShort && invalidChars.length === 0,
  }
}
