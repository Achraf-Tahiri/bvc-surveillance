"use client"

import { useState } from "react"
import { FORMATS, type Fmt } from "./formats"
import { useWidth } from "./use-width"

export type BarRow = { label: string; value: number; lo: number | null; hi: number | null; n?: number }

type Props = {
  rows: BarRow[]
  format: Fmt
  reference?: { value: number; label: string }
  axisLabel: string
  color?: string
}

const ROW = 34
const BAR = 16

/** Barres horizontales avec intervalle de confiance à 95 % et ligne de référence. */
export function BarsCI({ rows, format: fmt, reference, axisLabel, color = "var(--brand)" }: Props) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const format = FORMATS[fmt]
  const [hover, setHover] = useState<number | null>(null)
  const labelW = width < 520 ? 130 : 200
  const right = 56
  const plotW = Math.max(80, width - labelW - right)
  const max = Math.max(...rows.map((r) => r.hi ?? r.value), reference?.value ?? 0) * 1.05
  const x = (v: number) => labelW + (Math.max(0, v) / max) * plotW
  const ticks = niceTicks(max)
  const h = rows.length * ROW + 44

  return (
    <div ref={ref} className="relative w-full">
      <svg width={width} height={h} role="img" aria-label={axisLabel} className="block">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={8} y2={rows.length * ROW + 8} stroke="var(--grid)" strokeWidth={1} />
            <text x={x(t)} y={rows.length * ROW + 24} textAnchor="middle" fontSize={11} fill="var(--faint)" className="tabular">
              {format(t)}
            </text>
          </g>
        ))}
        {rows.map((r, i) => {
          const y = 8 + i * ROW + (ROW - BAR) / 2
          const active = hover === i
          return (
            <g
              key={r.label}
              onPointerEnter={() => setHover(i)}
              onPointerLeave={() => setHover(null)}
              onFocus={() => setHover(i)}
              onBlur={() => setHover(null)}
              tabIndex={0}
              aria-label={`${r.label} : ${format(r.value)}`}
              className="outline-none"
            >
              <rect x={0} y={8 + i * ROW} width={width} height={ROW} fill={active ? "var(--accent)" : "transparent"} />
              <text x={labelW - 12} y={y + BAR / 2 + 4} textAnchor="end" fontSize={12.5} fill="var(--ink-2)">
                {truncate(r.label, labelW < 150 ? 17 : 28)}
              </text>
              <path d={barPath(labelW, y, x(r.value) - labelW, BAR)} fill={color} opacity={hover == null || active ? 1 : 0.55} />
              {r.lo != null && r.hi != null && (
                <g stroke="var(--ink-2)" strokeWidth={1.25}>
                  <line x1={x(r.lo)} x2={x(r.hi)} y1={y + BAR / 2} y2={y + BAR / 2} />
                  <line x1={x(r.lo)} x2={x(r.lo)} y1={y + 3} y2={y + BAR - 3} />
                  <line x1={x(r.hi)} x2={x(r.hi)} y1={y + 3} y2={y + BAR - 3} />
                </g>
              )}
              <text x={x(r.hi ?? r.value) + 8} y={y + BAR / 2 + 4} fontSize={12} fill="var(--ink)" className="tabular">
                {format(r.value)}
              </text>
            </g>
          )
        })}
        {reference && (
          <g>
            <line x1={x(reference.value)} x2={x(reference.value)} y1={2} y2={rows.length * ROW + 10} stroke="var(--ink)" strokeWidth={1.25} strokeDasharray="4 3" />
          </g>
        )}
        <text x={labelW} y={h - 4} fontSize={11} fill="var(--faint)">
          {axisLabel}
        </text>
      </svg>
      {reference && (
        <p className="mt-1 text-xs text-muted-foreground">
          Ligne pointillée : {reference.label} ({format(reference.value)}). Traits fins : intervalle de confiance à 95 %.
        </p>
      )}
      {hover != null && (
        <div
          className="pointer-events-none absolute z-10 rounded-md border bg-popover px-3 py-2 text-xs shadow-sm"
          style={{ left: Math.min(width - 190, x(rows[hover].value) + 12), top: 8 + hover * ROW + ROW }}
        >
          <div className="text-sm font-semibold text-ink tabular">{format(rows[hover].value)}</div>
          <div className="text-ink-2">{rows[hover].label}</div>
          {rows[hover].lo != null && (
            <div className="text-muted-foreground tabular">
              IC 95 % : {format(rows[hover].lo!)} à {format(rows[hover].hi!)}
            </div>
          )}
          {rows[hover].n != null && <div className="text-muted-foreground">{rows[hover].n} événements</div>}
        </div>
      )}
    </div>
  )
}

function barPath(x: number, y: number, w: number, h: number) {
  const r = Math.min(4, w / 2)
  return `M${x},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h - r} Q${x + w},${y + h} ${x + w - r},${y + h} H${x} Z`
}

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n - 1) + "…" : s
}

export function niceTicks(max: number, count = 4): number[] {
  const raw = max / count
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw
  const out: number[] = []
  for (let t = 0; t <= max + 1e-9; t += step) out.push(+t.toFixed(10))
  return out
}
