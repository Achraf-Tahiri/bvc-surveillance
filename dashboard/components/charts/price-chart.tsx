"use client"

import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  CrosshairMode,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
} from "lightweight-charts"
import { useEffect, useMemo, useRef, useState } from "react"
import { CATEGORIES, compact, date, num, pct, TYPES } from "@/lib/format"
import type { Categorie, Cours } from "@/lib/types"
import { cn } from "@/lib/utils"
import { useChartTheme } from "./use-chart-theme"

export type Marque = { time: string; label: string }
export type MarqueAlerte = { time: string; categorie: Categorie; z: number }
export type MarquePublication = { time: string; title: string; type: string | null }

const RANGES = [
  { key: "6m", label: "6 mois", sessions: 125 },
  { key: "1a", label: "1 an", sessions: 250 },
  { key: "3a", label: "3 ans", sessions: 750 },
  { key: "tout", label: "Tout", sessions: Infinity },
] as const

type Props = {
  data: Cours[]
  alertes: MarqueAlerte[]
  publications: MarquePublication[]
}

export function PriceChart({ data, alertes, publications }: Props) {
  const box = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const theme = useChartTheme()
  const [range, setRange] = useState<(typeof RANGES)[number]["key"]>("1a")
  const [hover, setHover] = useState<string | null>(null)

  const byTime = useMemo(() => new Map(data.map((d, i) => [d.time, i])), [data])
  const alertByTime = useMemo(() => new Map(alertes.map((a) => [a.time, a])), [alertes])
  const pubsByTime = useMemo(() => {
    const m = new Map<string, MarquePublication[]>()
    for (const p of publications) m.set(p.time, [...(m.get(p.time) ?? []), p])
    return m
  }, [publications])

  useEffect(() => {
    if (!box.current || !theme) return
    const chart = createChart(box.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: theme.surface },
        textColor: theme.faint,
        fontFamily: getComputedStyle(document.body).fontFamily,
        fontSize: 11,
        attributionLogo: true,
        panes: { separatorColor: theme.grid, separatorHoverColor: theme.grid, enableResize: false },
      },
      grid: { vertLines: { visible: false }, horzLines: { color: theme.grid } },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: { color: theme.axis, labelBackgroundColor: theme.ink2 },
        horzLine: { color: theme.axis, labelBackgroundColor: theme.ink2 },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderColor: theme.axis, rightOffset: 4 },
      localization: {
        locale: "fr-FR",
        priceFormatter: (p: number) => num(p, 2),
        tickmarksPriceFormatter: (ps: number[]) => ps.map((p) => (p >= 1e5 ? compact(p) : num(p, p >= 1000 ? 0 : 2))),
      },
    })
    chartRef.current = chart

    const candles = chart.addSeries(CandlestickSeries, {
      upColor: theme.surface,
      downColor: theme.ink2,
      borderUpColor: theme.ink2,
      borderDownColor: theme.ink2,
      wickUpColor: theme.ink2,
      wickDownColor: theme.ink2,
      priceLineVisible: false,
    })
    candles.setData(
      data.map((d) => ({
        time: d.time as Time,
        open: d.open ?? d.close,
        high: d.high ?? Math.max(d.open ?? d.close, d.close),
        low: d.low ?? Math.min(d.open ?? d.close, d.close),
        close: d.close,
      })),
    )
    const volume: ISeriesApi<"Histogram"> = chart.addSeries(
      HistogramSeries,
      { color: theme.axis, priceFormat: { type: "volume" }, priceLineVisible: false, lastValueVisible: false },
      1,
    )
    volume.setData(data.map((d) => ({ time: d.time as Time, value: d.volume ?? 0 })))
    chart.panes()[1]?.setHeight(80)

    const marks: SeriesMarker<Time>[] = []
    for (const a of alertes) {
      if (!byTime.has(a.time)) continue
      marks.push({
        time: a.time as Time,
        position: a.z >= 0 ? "aboveBar" : "belowBar",
        shape: a.z >= 0 ? "arrowDown" : "arrowUp",
        color: theme[a.categorie === "expliquee" ? "expliquee" : a.categorie === "precede_publication" ? "precede" : "sans"],
        size: 1,
      })
    }
    for (const t of pubsByTime.keys()) {
      if (!byTime.has(t)) continue
      marks.push({ time: t as Time, position: "belowBar", shape: "circle", color: theme.faint, size: 0.1 })
    }
    marks.sort((a, b) => String(a.time).localeCompare(String(b.time)))
    createSeriesMarkers(candles, marks)

    chart.subscribeCrosshairMove((p) => setHover(p.time ? String(p.time) : null))
    return () => {
      chart.remove()
      chartRef.current = null
    }
  }, [data, alertes, byTime, pubsByTime, theme])

  useEffect(() => {
    const chart = chartRef.current
    if (!chart || data.length === 0) return
    const n = RANGES.find((r) => r.key === range)!.sessions
    if (!Number.isFinite(n) || n >= data.length) chart.timeScale().fitContent()
    else chart.timeScale().setVisibleLogicalRange({ from: data.length - n, to: data.length + 3 })
  }, [range, data, theme])

  const shown = data[hover ? (byTime.get(hover) ?? data.length - 1) : data.length - 1]
  const prev = shown ? data[(byTime.get(shown.time) ?? 0) - 1] : undefined
  const alerte = shown ? alertByTime.get(shown.time) : undefined
  const pubs = shown ? pubsByTime.get(shown.time) : undefined

  return (
    <div className="rounded-lg border bg-surface">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b px-4 py-3">
        <div className="min-h-[44px] text-sm">
          {shown && (
            <>
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 tabular">
                <span className="font-medium text-ink">{date(shown.time, true)}</span>
                <span className="text-ink-2">
                  Clôture <span className="font-medium text-ink">{num(shown.close)}</span>
                  {prev && <span className="ml-1.5">{pct((shown.close / prev.close - 1) * 100)}</span>}
                </span>
                {shown.open != null && (
                  <span className="space-x-2.5 text-muted-foreground">
                    <span>Ouv. {num(shown.open)}</span>
                    <span>Haut {num(shown.high)}</span>
                    <span>Bas {num(shown.low)}</span>
                  </span>
                )}
                <span className="text-muted-foreground">Titres échangés {compact(shown.volume)}</span>
              </div>
              <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-ink-2">
                {alerte && (
                  <span className="inline-flex items-center gap-1.5">
                    <span className="size-2 rounded-full" style={{ background: CATEGORIES[alerte.categorie].color }} />
                    Alerte ({CATEGORIES[alerte.categorie].label.toLowerCase()}), z = {num(alerte.z, 1)}
                  </span>
                )}
                {pubs?.map((p, i) => (
                  <span key={i} className="max-w-[60ch] truncate">
                    Publication : {p.title}
                    {p.type && <span className="text-muted-foreground"> ({TYPES[p.type] ?? p.type})</span>}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
        <div className="flex gap-1" role="group" aria-label="Période affichée">
          {RANGES.map((r) => (
            <button
              key={r.key}
              type="button"
              onClick={() => setRange(r.key)}
              aria-pressed={range === r.key}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs text-ink-2 transition-colors hover:bg-accent",
                range === r.key && "bg-accent font-medium text-ink",
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
      <div ref={box} className="h-[420px] w-full" />
      <Legend />
    </div>
  )
}

function Legend() {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 border-t px-4 py-2.5 text-xs text-ink-2">
      {(Object.keys(CATEGORIES) as Categorie[]).map((k) => (
        <span key={k} className="inline-flex items-center gap-1.5">
          <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden>
            <path d="M5 9 L1 2 H9 Z" fill={CATEGORIES[k].color} />
          </svg>
          Alerte : {CATEGORIES[k].label.toLowerCase()}
        </span>
      ))}
      <span className="inline-flex items-center gap-1.5">
        <span className="size-1.5 rounded-full bg-faint" />
        Publication AMMC (jour de réaction)
      </span>
      <span className="text-muted-foreground">Bougies creuses : hausse ; pleines : baisse. Volume en titres.</span>
    </div>
  )
}
