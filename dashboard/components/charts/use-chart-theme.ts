"use client"

import { useTheme } from "next-themes"
import { useMemo } from "react"

export type ChartTheme = {
  surface: string
  ink: string
  ink2: string
  faint: string
  grid: string
  axis: string
  brand: string
  expliquee: string
  precede: string
  sans: string
  up: string
  down: string
}

const VARS: Record<keyof ChartTheme, string> = {
  surface: "--surface",
  ink: "--ink",
  ink2: "--ink-2",
  faint: "--faint",
  grid: "--grid",
  axis: "--axis",
  brand: "--brand",
  expliquee: "--cat-expliquee",
  precede: "--cat-precede",
  sans: "--cat-sans",
  up: "--up",
  down: "--down",
}

/** Couleurs du thème courant, lues dans les variables CSS (clair ou sombre). */
export function useChartTheme(): ChartTheme | null {
  const { resolvedTheme } = useTheme()
  return useMemo(() => {
    // Rien à lire côté serveur ; le graphique est créé dans le navigateur.
    if (typeof document === "undefined" || !resolvedTheme) return null
    const style = getComputedStyle(document.documentElement)
    const out = {} as ChartTheme
    for (const [k, v] of Object.entries(VARS)) out[k as keyof ChartTheme] = style.getPropertyValue(v).trim()
    return out
  }, [resolvedTheme])
}
