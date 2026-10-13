"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import { CategoryBadge } from "@/components/bits"
import { CATEGORIES, date, num, pct, signed, TYPES } from "@/lib/format"
import type { Alerte, Categorie } from "@/lib/types"

const PERIODES = { direct: "Collecte en direct", test: "Test (2023 à 2026)", entrainement: "Entraînement (2013 à 2022)" }
const PAGE = 50

const selectCls =
  "h-9 rounded-md border bg-surface px-2.5 text-sm text-ink outline-none focus-visible:ring-2 focus-visible:ring-ring"

export function AlertsTable({ alertes, compact = false }: { alertes: Alerte[]; compact?: boolean }) {
  const [valeur, setValeur] = useState("")
  const [categorie, setCategorie] = useState("")
  const [periode, setPeriode] = useState("")
  const [annee, setAnnee] = useState("")
  const [shown, setShown] = useState(PAGE)

  const valeurs = useMemo(
    () => [...new Map(alertes.map((a) => [a.ticker, a.name ?? a.ticker])).entries()].sort((a, b) => a[1].localeCompare(b[1], "fr")),
    [alertes],
  )
  const annees = useMemo(() => [...new Set(alertes.map((a) => a.day.slice(0, 4)))].sort().reverse(), [alertes])
  const rows = useMemo(
    () =>
      alertes.filter(
        (a) =>
          (!valeur || a.ticker === valeur) &&
          (!categorie || a.categorie === categorie) &&
          (!periode || a.periode === periode) &&
          (!annee || a.day.startsWith(annee)),
      ),
    [alertes, valeur, categorie, periode, annee],
  )
  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const r of rows) c[r.categorie] = (c[r.categorie] ?? 0) + 1
    return c
  }, [rows])

  return (
    <div>
      {!compact && (
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <Field label="Année">
            <select className={selectCls} value={annee} onChange={(e) => (setAnnee(e.target.value), setShown(PAGE))}>
              <option value="">Toutes</option>
              {annees.map((y) => (
                <option key={y}>{y}</option>
              ))}
            </select>
          </Field>
          <Field label="Valeur">
            <select className={selectCls} value={valeur} onChange={(e) => (setValeur(e.target.value), setShown(PAGE))}>
              <option value="">Toutes</option>
              {valeurs.map(([t, n]) => (
                <option key={t} value={t}>
                  {n}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Catégorie">
            <select className={selectCls} value={categorie} onChange={(e) => (setCategorie(e.target.value), setShown(PAGE))}>
              <option value="">Toutes</option>
              {(Object.keys(CATEGORIES) as Categorie[]).map((k) => (
                <option key={k} value={k}>
                  {CATEGORIES[k].label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Période">
            <select className={selectCls} value={periode} onChange={(e) => (setPeriode(e.target.value), setShown(PAGE))}>
              <option value="">Toutes</option>
              {Object.entries(PERIODES).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </Field>
          <div className="ml-auto text-sm text-muted-foreground tabular">
            {rows.length} alertes
            {(Object.keys(CATEGORIES) as Categorie[]).map((k) => (
              <span key={k} className="ml-3 inline-flex items-center gap-1">
                <span className="size-2 rounded-full" style={{ background: CATEGORIES[k].color }} />
                {counts[k] ?? 0}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border bg-surface">
        <table className="w-full min-w-[760px] text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="px-4 py-2.5 font-medium">Séance</th>
              {!compact && <th className="px-3 py-2.5 font-medium">Valeur</th>}
              <th className="px-3 py-2.5 text-right font-medium">Rendement</th>
              <th className="px-3 py-2.5 text-right font-medium" title="Rendement anormal divisé par son écart type habituel">
                z
              </th>
              <th className="px-3 py-2.5 text-right font-medium" title="Écart à la médiane des 250 séances précédentes, en écarts robustes">
                Volume anormal
              </th>
              <th className="px-3 py-2.5 font-medium">Catégorie</th>
              <th className="px-4 py-2.5 font-medium">Publication la plus proche</th>
            </tr>
          </thead>
          <tbody className="divide-y tabular">
            {rows.slice(0, shown).map((a) => (
              <tr key={`${a.ticker}${a.day}`} className="align-top transition-colors hover:bg-accent/60">
                <td className="whitespace-nowrap px-4 py-2.5 text-ink-2">{date(a.day)}</td>
                {!compact && (
                  <td className="px-3 py-2.5">
                    <Link href={`/valeurs/${a.ticker}`} className="font-medium text-ink underline-offset-4 hover:underline">
                      {a.name ?? a.ticker}
                    </Link>
                  </td>
                )}
                <td className="px-3 py-2.5 text-right text-ink">{pct((a.rendement ?? 0) * 100, 1)}</td>
                <td className="px-3 py-2.5 text-right text-ink-2">{signed(a.z, 1)}</td>
                <td className="px-3 py-2.5 text-right text-ink-2">{signed(a.abvol, 1)}</td>
                <td className="px-3 py-2.5">
                  <CategoryBadge categorie={a.categorie} />
                </td>
                <td className="max-w-[26rem] px-4 py-2.5 text-ink-2">
                  {a.communique_title ? (
                    <>
                      <div className="truncate text-ink" title={a.communique_title}>
                        {a.communique_title}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {a.communique_type ? TYPES[a.communique_type] : ""}, jour de réaction {date(a.communique_day0)} (
                        {a.ecart_seances === 0
                          ? "même séance"
                          : `${signed(a.ecart_seances ?? 0, 0)} séance${Math.abs(a.ecart_seances ?? 0) > 1 ? "s" : ""}`}
                        )
                      </div>
                    </>
                  ) : (
                    <span className="text-muted-foreground">Aucune dans [−1, +10] séances</span>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-muted-foreground">
                  Aucune alerte pour ces filtres.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {rows.length > shown && (
        <button
          type="button"
          onClick={() => setShown((s) => s + PAGE)}
          className="mt-4 rounded-md border bg-surface px-4 py-2 text-sm text-ink transition-colors hover:bg-accent active:scale-[0.98]"
        >
          Afficher {Math.min(PAGE, rows.length - shown)} de plus ({num(rows.length - shown, 0)} restantes)
        </button>
      )}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-xs text-muted-foreground">
      {label}
      {children}
    </label>
  )
}
