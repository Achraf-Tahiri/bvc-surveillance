"use client"

import { AreaSeries, ColorType, createChart, CrosshairMode, type IChartApi, type Time } from "lightweight-charts"
import { useEffect, useMemo, useRef, useState } from "react"
import { date, num, pct } from "@/lib/format"
import type { Point } from "@/lib/types"
import { cn } from "@/lib/utils"
import { useChartTheme } from "./use-chart-theme"

const RANGES = [
  { key: "1a", label: "1 an", sessions: 250 },
  { key: "5a", label: "5 ans", sessions: 1250 },
  { key: "tout", label: "Tout", sessions: Infinity },
] as const

export function IndexChart({ data, name }: { data: Point[]; name: string }) {
  const box = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const theme = useChartTheme()
  const [range, setRange] = useState<(typeof RANGES)[number]["key"]>("5a")
  const [hover, setHover] = useState<string | null>(null)
  const idx = useMemo(() => new Map(data.map((d, i) => [d.time, i])), [data])

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
      },
      grid: { vertLines: { visible: false }, horzLines: { color: theme.grid } },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: { color: theme.axis, labelBackgroundColor: theme.ink2 },
        horzLine: { visible: false, labelVisible: false },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderColor: theme.axis },
      handleScroll: false,
      handleScale: false,
      localization: { locale: "fr-FR", priceFormatter: (p: number) => num(p, 0), tickmarksPriceFormatter: (ps: number[]) => ps.map((p) => num(p, 0)) },
    })
    chartRef.current = chart
    const s = chart.addSeries(AreaSeries, {
      lineColor: theme.brand,
      lineWidth: 2,
      topColor: theme.brand + "26",
      bottomColor: theme.brand + "00",
      priceLineVisible: false,
      crosshairMarkerRadius: 4,
      crosshairMarkerBorderColor: theme.surface,
      crosshairMarkerBorderWidth: 2,
    })
    s.setData(data.map((d) => ({ time: d.time as Time, value: d.value })))
    chart.subscribeCrosshairMove((p) => setHover(p.time ? String(p.time) : null))
    return () => {
      chart.remove()
      chartRef.current = null
    }
  }, [data, theme])

  useEffect(() => {
    const chart = chartRef.current
    if (!chart || data.length === 0) return
    const n = RANGES.find((r) => r.key === range)!.sessions
    if (!Number.isFinite(n) || n >= data.length) chart.timeScale().fitContent()
    else chart.timeScale().setVisibleLogicalRange({ from: data.length - n, to: data.length - 1 })
  }, [range, data, theme])

  const n = RANGES.find((r) => r.key === range)!.sessions
  const shown = data[hover ? (idx.get(hover) ?? data.length - 1) : data.length - 1]
  const first = data[Number.isFinite(n) ? Math.max(0, data.length - n) : 0]

  return (
    <div className="rounded-lg border bg-surface">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 pt-3">
        <div className="text-sm tabular">
          {shown && (
            <span className="text-ink-2">
              {name} le {date(shown.time, true)} :{" "}
              <span className="font-medium text-ink">{num(shown.value, 2)}</span>
              {!hover && first && (
                <span className="ml-2 text-muted-foreground">
                  {pct((shown.value / first.value - 1) * 100, 1)} sur la période
                </span>
              )}
            </span>
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
      <div ref={box} className="h-[260px] w-full" />
    </div>
  )
}
