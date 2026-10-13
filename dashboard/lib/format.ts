const nf = (d: number) =>
  new Intl.NumberFormat("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d })

export function num(v: number | null | undefined, d = 2): string {
  return v == null || !Number.isFinite(v) ? "n.d." : nf(d).format(v)
}

export function signed(v: number | null | undefined, d = 2, suffix = ""): string {
  if (v == null || !Number.isFinite(v)) return "n.d."
  const s = nf(d).format(Math.abs(v))
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${s}${suffix}`
}

export function pct(v: number | null | undefined, d = 2): string {
  return signed(v, d, " %")
}

export function compact(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "n.d."
  return new Intl.NumberFormat("fr-FR", { notation: "compact", maximumFractionDigits: 1 }).format(v)
}

const MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]

export function date(iso: string | null | undefined, long = false): string {
  if (!iso) return "n.d."
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number)
  if (long) return `${d} ${MONTHS[m - 1]} ${y}`
  return `${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}/${y}`
}

export const TYPES: Record<string, string> = {
  resultats: "Résultats",
  profit_warning: "Profit warning",
  indicateurs_trimestriels: "Indicateurs trimestriels",
  assemblee_generale: "Assemblée générale",
  operation_financiere: "Opération financière",
  dette: "Dette",
  gouvernance: "Gouvernance",
  autre: "Autre",
}

export const CATEGORIES = {
  expliquee: { label: "Expliquée", long: "Publication à une séance près", color: "var(--cat-expliquee)" },
  precede_publication: { label: "Précède une publication", long: "Publication 2 à 10 séances après", color: "var(--cat-precede)" },
  sans_explication: { label: "Sans explication", long: "Aucune publication à proximité", color: "var(--cat-sans)" },
} as const
