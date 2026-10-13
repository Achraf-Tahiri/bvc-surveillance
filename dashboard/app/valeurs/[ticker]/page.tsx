import type { Metadata } from "next"
import { notFound } from "next/navigation"
import { Suspense } from "react"
import { AlertsTable } from "@/components/alerts-table"
import { Section, Stat } from "@/components/bits"
import { PriceChart } from "@/components/charts/price-chart"
import reactions from "@/data/reactions.json"
import { getAlerts, getInstruments, getPrices, getPublications } from "@/lib/data"
import { date, num, pct, TYPES } from "@/lib/format"
import { jourReaction } from "@/lib/jour0"

type Reaction = { day0: string; event_type: string; title: string; car_ann_pct: number; vr_ann: number; abvol_ann: number; liquid: boolean }
const REACTIONS = reactions as Record<string, Reaction[]>

export async function generateStaticParams() {
  const valeurs = await getInstruments()
  return valeurs.filter((v) => v.n_days > 0).map((v) => ({ ticker: v.ticker }))
}

export async function generateMetadata({ params }: PageProps<"/valeurs/[ticker]">): Promise<Metadata> {
  const { ticker } = await params
  const v = (await getInstruments()).find((i) => i.ticker === ticker)
  return { title: v?.name ?? ticker }
}

export default function ValeurPage(props: PageProps<"/valeurs/[ticker]">) {
  return (
    <Suspense fallback={<div className="h-[640px] animate-pulse rounded-lg bg-muted" />}>
      <Valeur params={props.params} />
    </Suspense>
  )
}

async function Valeur({ params }: { params: PageProps<"/valeurs/[ticker]">["params"] }) {
  const { ticker } = await params
  const [valeurs, cours, toutes, pubs] = await Promise.all([
    getInstruments(),
    getPrices(ticker),
    getAlerts(),
    getPublications(ticker),
  ])
  const v = valeurs.find((i) => i.ticker === ticker)
  if (!v || cours.length === 0) notFound()

  const alertes = toutes.filter((a) => a.ticker === ticker)
  const days = cours.map((c) => c.time)
  const marquesPubs = pubs
    .map((p) => ({ time: jourReaction(p.published_at, days), title: p.title, type: p.event_type }))
    .filter((p): p is { time: string; title: string; type: string | null } => p.time != null)
  const passees = REACTIONS[ticker] ?? []
  const fortes = [...passees].sort((a, b) => Math.abs(b.car_ann_pct) - Math.abs(a.car_ann_pct)).slice(0, 12)
  const last = cours[cours.length - 1]
  const prev = cours[cours.length - 2]

  return (
    <>
      <div className="mb-6">
        <p className="text-sm text-muted-foreground">
          {v.sector}
          {v.in_masi20 && <span> · membre du MASI 20</span>}
        </p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-ink md:text-4xl">
          {v.name} <span className="text-xl font-normal text-faint">{ticker}</span>
        </h1>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-x-6 gap-y-4 border-y py-5 md:grid-cols-4">
        <Stat
          note={prev && (Date.parse(last.time) - Date.parse(prev.time)) / 86400000 > 10 ? `par rapport au ${date(prev.time)}` : undefined}
          label={`Clôture du ${date(last.time)}`}
          value={num(last.close)}
          delta={prev ? pct((last.close / prev.close - 1) * 100) : undefined}
          deltaTone={prev ? (last.close > prev.close ? "up" : last.close < prev.close ? "down" : "flat") : undefined}
        />
        <Stat label="Séances avec cours" value={num(cours.length, 0)} note={`depuis le ${date(cours[0].time)}`} />
        <Stat label="Alertes" value={`${alertes.length}`} note={alertes[0] ? `dernière le ${date(alertes[0].day)}` : undefined} />
        <Stat label="Publications AMMC" value={`${pubs.length}`} note={`${passees.length} retenues dans l'étude`} />
      </div>

      <PriceChart
        data={cours}
        alertes={alertes.map((a) => ({ time: a.day, categorie: a.categorie, z: a.z }))}
        publications={marquesPubs}
      />
      <p className="mt-2 text-xs text-muted-foreground">
        Historique ajusté des divisions de titres jusqu&apos;au 27/03/2026, cours collectés en direct (non ajustés) depuis
        le 13/10/2026.
      </p>

      <Section title="Alertes sur cette valeur">
        {alertes.length ? (
          <AlertsTable alertes={alertes} compact />
        ) : (
          <p className="text-sm text-muted-foreground">Aucune séance atypique détectée.</p>
        )}
      </Section>

      <Section title="Réactions passées aux publications">
        {fortes.length ? (
          <>
            <p className="mb-3 max-w-[72ch] text-sm text-ink-2">
              Les {fortes.length} plus fortes réactions sur les séances 0 et +1 (rendement anormal cumulé par rapport au
              MASI). Rapport de variance : 1 = séance ordinaire.
            </p>
            <div className="overflow-x-auto rounded-lg border bg-surface">
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="px-4 py-2.5 font-medium">Jour de réaction</th>
                    <th className="px-3 py-2.5 font-medium">Publication</th>
                    <th className="px-3 py-2.5 text-right font-medium">Rendement anormal [0, +1]</th>
                    <th className="px-4 py-2.5 text-right font-medium">Rapport de variance</th>
                  </tr>
                </thead>
                <tbody className="divide-y tabular">
                  {fortes.map((r) => (
                    <tr key={r.day0 + r.title}>
                      <td className="whitespace-nowrap px-4 py-2 text-ink-2">{date(r.day0)}</td>
                      <td className="max-w-[28rem] px-3 py-2">
                        <div className="truncate text-ink" title={r.title}>
                          {r.title}
                        </div>
                        <div className="text-xs text-muted-foreground">{TYPES[r.event_type] ?? r.event_type}</div>
                      </td>
                      <td className="px-3 py-2 text-right text-ink">{pct(r.car_ann_pct, 1)}</td>
                      <td className="px-4 py-2 text-right text-ink-2">{num(r.vr_ann, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">Pas assez d&apos;historique pour l&apos;étude d&apos;événements.</p>
        )}
      </Section>

      <Section title="Publications récentes">
        <ul className="divide-y rounded-lg border bg-surface">
          {pubs.slice(0, 10).map((p) => (
            <li key={p.published_at + p.title} className="flex items-baseline justify-between gap-4 px-4 py-2.5 text-sm">
              <span className="min-w-0">
                {p.pdf_url ? (
                  <a href={p.pdf_url} className="text-ink underline-offset-4 hover:underline">
                    {p.title}
                  </a>
                ) : (
                  <span className="text-ink">{p.title}</span>
                )}
                <span className="ml-2 text-xs text-muted-foreground">{p.event_type ? TYPES[p.event_type] : ""}</span>
              </span>
              <span className="shrink-0 text-muted-foreground tabular">{date(p.published_at)}</span>
            </li>
          ))}
          {pubs.length === 0 && <li className="px-4 py-6 text-sm text-muted-foreground">Aucune publication rattachée.</li>}
        </ul>
      </Section>
    </>
  )
}
