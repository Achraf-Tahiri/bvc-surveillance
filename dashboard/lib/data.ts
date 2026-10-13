"use cache"

import { cacheLife } from "next/cache"
import { db } from "./db"
import type { Alerte, Cours, Instrument, Point, Publication, Seance } from "./types"

// Neon (offre gratuite) se met en veille après 5 minutes : les pages sont générées
// à l'avance et rafraîchies au plus une fois par heure (équivalent de revalidate = 3600).
const HOUR = { stale: 300, revalidate: 3600, expire: 30 * 86400 }

export async function getLastSession(): Promise<Seance | null> {
  cacheLife(HOUR)
  const rows = await db()<Seance[]>`
    SELECT s.session_date::text AS session_date, s.market_status, s.masi, s.masi_var_pct,
           s.masi20, s.masi20_var_pct, s.capitalisation_mad, s.volume_global_mad,
           (SELECT count(*)::int FROM live_stocks l WHERE l.session_date = s.session_date AND l.status = 'T') AS traitees,
           (SELECT count(*)::int FROM live_stocks l WHERE l.session_date = s.session_date) AS valeurs
    FROM live_sessions s ORDER BY s.session_date DESC LIMIT 1`
  return rows[0] ?? null
}

export async function getIndexSeries(ticker: string): Promise<Point[]> {
  cacheLife(HOUR)
  return db()<Point[]>`
    SELECT day::text AS time, close AS value FROM prices_daily WHERE ticker = ${ticker} ORDER BY day`
}

export async function getAlerts(): Promise<Alerte[]> {
  cacheLife(HOUR)
  return db()<Alerte[]>`
    SELECT a.ticker, i.name, a.day::text AS day, a.score, a.iforest, a.regles, a.z, a.rendement,
           a.abvol, a.vol_ratio, a.categorie, a.communique_title, a.communique_type,
           a.communique_day0::text AS communique_day0, a.ecart_seances, a.periode
    FROM alerts a LEFT JOIN instruments i USING (ticker)
    ORDER BY a.day DESC, a.score DESC`
}

export async function getInstruments(): Promise<Instrument[]> {
  cacheLife(HOUR)
  return db()<Instrument[]>`
    SELECT i.ticker, i.name, i.sector, i.in_masi20, p.day::text AS last_day, p.close AS last_close,
           (SELECT count(*)::int FROM alerts a WHERE a.ticker = i.ticker) AS n_alerts,
           (SELECT count(*)::int FROM prices_daily d WHERE d.ticker = i.ticker) AS n_days
    FROM instruments i
    LEFT JOIN LATERAL (SELECT day, close FROM prices_daily d WHERE d.ticker = i.ticker
                       ORDER BY day DESC LIMIT 1) p ON true
    WHERE i.kind = 'stock' AND i.sector IS NOT NULL
    ORDER BY i.name`
}

export async function getPrices(ticker: string): Promise<Cours[]> {
  cacheLife(HOUR)
  return db()<Cours[]>`
    SELECT day::text AS time, open, high, low, close, volume
    FROM prices_daily WHERE ticker = ${ticker} ORDER BY day`
}

export async function getPublications(ticker: string): Promise<Publication[]> {
  cacheLife(HOUR)
  return db()<Publication[]>`
    SELECT to_char(published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS published_at,
           title, event_type, pdf_url, ticker, NULL::text AS name
    FROM communiques WHERE ticker = ${ticker} ORDER BY published_at DESC`
}

export async function getRecentPublications(limit: number): Promise<Publication[]> {
  cacheLife(HOUR)
  return db()<Publication[]>`
    SELECT to_char(c.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS published_at,
           c.title, c.event_type, c.pdf_url, c.ticker, i.name
    FROM communiques c LEFT JOIN instruments i USING (ticker)
    ORDER BY c.published_at DESC LIMIT ${limit}`
}
