export type Categorie = "expliquee" | "precede_publication" | "sans_explication"

export type Alerte = {
  ticker: string
  name: string | null
  day: string
  score: number
  iforest: boolean
  regles: string | null
  z: number
  rendement: number | null
  abvol: number | null
  vol_ratio: number | null
  categorie: Categorie
  communique_title: string | null
  communique_type: string | null
  communique_day0: string | null
  ecart_seances: number | null
  periode: "entrainement" | "test" | "direct"
}

export type Seance = {
  session_date: string
  market_status: string | null
  masi: number | null
  masi_var_pct: number | null
  masi20: number | null
  masi20_var_pct: number | null
  capitalisation_mad: number | null
  volume_global_mad: number | null
  traitees: number
  valeurs: number
}

export type Instrument = {
  ticker: string
  name: string | null
  sector: string | null
  in_masi20: boolean | null
  last_day: string | null
  last_close: number | null
  n_alerts: number
  n_days: number
}

export type Cours = {
  time: string
  open: number | null
  high: number | null
  low: number | null
  close: number
  volume: number | null
}

export type Publication = {
  published_at: string
  title: string
  event_type: string | null
  pdf_url: string | null
  ticker: string | null
  name: string | null
}

export type Point = { time: string; value: number }
