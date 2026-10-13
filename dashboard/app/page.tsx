import Link from "next/link"
import { CategoryBadge, MoreLink, Section, Stat } from "@/components/bits"
import { IndexChart } from "@/components/charts/index-chart"
import { getAlerts, getIndexSeries, getLastSession, getRecentPublications } from "@/lib/data"
import { date, num, pct, TYPES } from "@/lib/format"
import { validationTest } from "@/lib/resultats"

function tone(v: number | null | undefined) {
  return v == null ? undefined : v > 0 ? "up" : v < 0 ? "down" : "flat"
}

export default async function Home() {
  const [seance, masi, alertes, publications] = await Promise.all([
    getLastSession(),
    getIndexSeries("MASI"),
    getAlerts(),
    getRecentPublications(8),
  ])
  const jour = seance?.session_date
  const duJour = alertes.filter((a) => a.day === jour)
  const derniere = alertes[0]?.day
  const recentes = alertes.slice(0, 10)
  const v = validationTest("alertes (Isolation Forest ou |z| > 4)")

  return (
    <>
      <div className="mb-8 max-w-[75ch]">
        <p className="text-sm text-muted-foreground">{seance?.market_status ?? "Séance"}</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-ink md:text-4xl">
          Séance du {date(jour, true)}
        </h1>
        <p className="mt-3 text-base leading-relaxed text-ink-2">
          Cours collectés chaque jour après la clôture, détection des séances atypiques par Isolation Forest et
          rapprochement automatique avec les publications des émetteurs (AMMC).
        </p>
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-4 border-y py-5 md:grid-cols-4">
        <Stat label="MASI" value={num(seance?.masi, 2)} delta={pct(seance?.masi_var_pct)} deltaTone={tone(seance?.masi_var_pct)} />
        <Stat label="MASI 20" value={num(seance?.masi20, 2)} delta={pct(seance?.masi20_var_pct)} deltaTone={tone(seance?.masi20_var_pct)} />
        <Stat label="Valeurs échangées" value={`${seance?.traitees ?? 0}`} note={`sur ${seance?.valeurs ?? 0} cotées`} />
        <Stat
          label="Alertes de la séance"
          value={`${duJour.length}`}
          note={duJour.length ? undefined : `Dernière alerte : ${date(derniere)}`}
        />
      </div>

      <Section title="MASI">
        <IndexChart data={masi} name="MASI" />
        <p className="mt-2 text-xs text-muted-foreground">
          Historique jusqu&apos;au 27/03/2026, puis collecte quotidienne depuis le 13/10/2026 : la période intermédiaire
          n&apos;est pas disponible.
        </p>
      </Section>

      <div className="grid gap-x-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] [&>*]:min-w-0">
        <Section title="Dernières alertes" aside={<MoreLink href="/alertes">Toutes les alertes</MoreLink>}>
          {duJour.length === 0 && (
            <p className="mb-3 text-sm text-muted-foreground">
              Aucune alerte sur la séance du {date(jour)}. Les plus récentes :
            </p>
          )}
          <ul className="divide-y rounded-lg border bg-surface">
            {recentes.map((a) => (
              <li key={`${a.ticker}${a.day}`}>
                <Link
                  href={`/valeurs/${a.ticker}`}
                  className="grid grid-cols-[5.5rem_1fr_auto] items-center gap-x-3 gap-y-1 px-4 py-2.5 text-sm transition-colors hover:bg-accent"
                >
                  <span className="text-muted-foreground tabular">{date(a.day)}</span>
                  <span className="min-w-0">
                    <span className="font-medium text-ink">{a.name ?? a.ticker}</span>
                    <span className="ml-2 text-ink-2 tabular">{pct((a.rendement ?? 0) * 100, 1)}</span>
                  </span>
                  <CategoryBadge categorie={a.categorie} className="justify-self-end" />
                </Link>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Dernières publications (AMMC)">
          <ul className="divide-y rounded-lg border bg-surface">
            {publications.map((p) => (
              <li key={p.published_at + p.title} className="px-4 py-2.5 text-sm">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="truncate text-ink">{p.title}</span>
                  <span className="shrink-0 text-muted-foreground tabular">{date(p.published_at)}</span>
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {p.event_type ? TYPES[p.event_type] : "Non classée"}
                  {p.ticker && (
                    <>
                      {" "}
                      sur{" "}
                      <Link className="text-primary underline-offset-4 hover:underline" href={`/valeurs/${p.ticker}`}>
                        {p.name ?? p.ticker}
                      </Link>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      </div>

      <Section title="La détection fonctionne-t-elle ?">
        <div className="grid gap-6 rounded-lg border bg-surface p-5 md:grid-cols-[auto_1fr] md:items-center">
          <div>
            <div className="text-5xl font-semibold tracking-tight text-ink">×{num(v.gain, 2)}</div>
            <div className="mt-1 text-sm text-muted-foreground tabular">
              IC 95 % : {num(v.gain_ic_bas, 2)} à {num(v.gain_ic_haut, 2)}
            </div>
          </div>
          <p className="max-w-[60ch] text-[15px] leading-relaxed text-ink-2">
            Sur 2023 à mars 2026, période jamais utilisée pour régler le modèle, {num(v.part_proche_pct, 1)} % des{" "}
            {v.alertes} alertes tombent à moins de deux séances d&apos;une publication de la valeur, contre{" "}
            {num(v.part_hasard_pct, 1)} % pour des séances tirées au hasard dans les mêmes valeurs.{" "}
            <MoreLink href="/methode">Méthode et limites</MoreLink>
          </p>
        </div>
      </Section>
    </>
  )
}
