"use client"

import { useState } from "react"
import { FORMATS, type Fmt } from "./formats"
import { useWidth } from "./use-width"

export type Serie = {
  name: string
  color: string
  y: number[]
  lo?: number[]
  hi?: number[]
  kind?: "line" | "bar"
  dashed?: boolean
}

type Props = {
  x: number[]
  series: Serie[]
  format: Fmt
  xLabel: string
  yLabel: string
  highlight?: [number, number]
  zero?: boolean
  height?: number
}

/** Profil sur des séances relatives (-10 à +10) : lignes ou barres, une seule échelle,
 *  repère vertical au survol et infobulle listant toutes les séries. */
export function ProfileChart({ x, series, format: fmt, xLabel, yLabel, highlight, zero, height = 280 }: Props) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const format = FORMATS[fmt]
  const [hover, setHover] = useState<number | null>(null)
  const m = { l: 52, r: 16, t: 14, b: 40 }
  const w = width - m.l - m.r
  const h = height - m.t - m.b
  const all = series.flatMap((s) => [...s.y, ...(s.lo ?? []), ...(s.hi ?? [])])
  let lo = Math.min(...all, zero || series.some((s) => s.kind === "bar") ? 0 : Infinity)
  let hi = Math.max(...all)
  const pad = (hi - lo) * 0.08
  lo -= lo < 0 ? pad : 0
  hi += pad
  const step = w / x.length
  const px = (i: number) => m.l + step * (i + 0.5)
  const py = (v: number) => m.t + h - ((v - lo) / (hi - lo)) * h
  const ticks = yTicks(lo, hi)
  const bars = series.filter((s) => s.kind === "bar")
  const barW = Math.min(24, (step * 0.7) / Math.max(1, bars.length))

  return (
    <div ref={ref} className="relative w-full">
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={`${yLabel} selon ${xLabel}`}
        className="block touch-none"
        onPointerMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect()
          const i = Math.floor((e.clientX - r.left - m.l) / step)
          setHover(i >= 0 && i < x.length ? i : null)
        }}
        onPointerLeave={() => setHover(null)}
      >
        {highlight && (
          <rect
            x={m.l + step * x.indexOf(highlight[0])}
            width={step * (highlight[1] - highlight[0] + 1)}
            y={m.t}
            height={h}
            fill="var(--accent)"
          />
        )}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={m.l} x2={m.l + w} y1={py(t)} y2={py(t)} stroke={t === 0 ? "var(--axis)" : "var(--grid)"} />
            <text x={m.l - 8} y={py(t) + 4} textAnchor="end" fontSize={11} fill="var(--faint)" className="tabular">
              {format(t)}
            </text>
          </g>
        ))}
        {x.map((v, i) =>
          v % 2 === 0 || width > 720 ? (
            <text key={v} x={px(i)} y={m.t + h + 16} textAnchor="middle" fontSize={11} fill="var(--faint)" className="tabular">
              {v > 0 ? `+${v}` : v}
            </text>
          ) : null,
        )}
        <text x={m.l} y={height - 4} fontSize={11} fill="var(--faint)">
          {xLabel}
        </text>
        {bars.map((s, k) =>
          s.y.map((v, i) => {
            const x0 = px(i) - (barW * bars.length) / 2 + k * barW + 1
            const y0 = py(Math.max(v, 0))
            const hh = Math.abs(py(v) - py(0))
            return (
              <rect key={`${s.name}${i}`} x={x0} y={y0} width={barW - 2} height={hh} rx={Math.min(3, hh / 2)} fill={s.color} opacity={hover == null || hover === i ? 1 : 0.6} />
            )
          }),
        )}
        {series
          .filter((s) => s.kind !== "bar")
          .map((s) => (
            <g key={s.name}>
              {s.lo && s.hi && (
                <path
                  d={`M${s.lo.map((v, i) => `${px(i)},${py(v)}`).join(" L")} L${s.hi
                    .map((v, i) => `${px(i)},${py(v)}`)
                    .reverse()
                    .join(" L")} Z`}
                  fill={s.color}
                  opacity={0.12}
                />
              )}
              <path
                d={`M${s.y.map((v, i) => `${px(i)},${py(v)}`).join(" L")}`}
                fill="none"
                stroke={s.color}
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
                strokeDasharray={s.dashed ? "5 4" : undefined}
              />
            </g>
          ))}
        {hover != null && (
          <g>
            <line x1={px(hover)} x2={px(hover)} y1={m.t} y2={m.t + h} stroke="var(--axis)" />
            {series
              .filter((s) => s.kind !== "bar")
              .map((s) => (
                <circle key={s.name} cx={px(hover)} cy={py(s.y[hover])} r={4} fill={s.color} stroke="var(--surface)" strokeWidth={2} />
              ))}
          </g>
        )}
      </svg>
      <Legend series={series} />
      {hover != null && (
        <div
          className="pointer-events-none absolute z-10 min-w-40 rounded-md border bg-popover px-3 py-2 text-xs shadow-sm"
          style={{ left: Math.min(width - 230, px(hover) + 14), top: m.t + 4 }}
        >
          <div className="mb-1 text-muted-foreground">
            Séance {x[hover] > 0 ? `+${x[hover]}` : x[hover]}
          </div>
          {series.map((s) => (
            <div key={s.name} className="flex items-center gap-2 py-0.5">
              <span className="h-0.5 w-3 rounded-full" style={{ background: s.color }} />
              <span className="font-semibold text-ink tabular">{format(s.y[hover])}</span>
              <span className="truncate text-ink-2">{s.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Legend({ series }: { series: Serie[] }) {
  if (series.length < 2) return null
  return (
    <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-2">
      {series.map((s) => (
        <span key={s.name} className="inline-flex items-center gap-1.5">
          {s.kind === "bar" ? (
            <span className="size-2.5 rounded-[3px]" style={{ background: s.color }} />
          ) : (
            <svg width="16" height="4" aria-hidden>
              <line x1="1" x2="15" y1="2" y2="2" stroke={s.color} strokeWidth="2" strokeLinecap="round" strokeDasharray={s.dashed ? "4 3" : undefined} />
            </svg>
          )}
          {s.name}
        </span>
      ))}
    </div>
  )
}

function yTicks(lo: number, hi: number, count = 5): number[] {
  const raw = (hi - lo) / count
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((k) => k * mag).find((s) => s >= raw) ?? raw
  const out: number[] = []
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) out.push(+t.toFixed(10))
  return out
}
