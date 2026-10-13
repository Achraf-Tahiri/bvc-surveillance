import type { Metadata } from "next"
import Link from "next/link"
import { PageTitle } from "@/components/bits"
import { getInstruments } from "@/lib/data"
import { date, num } from "@/lib/format"

export const metadata: Metadata = { title: "Valeurs" }

export default async function ValeursPage() {
  const valeurs = await getInstruments()
  const parSecteur = new Map<string, typeof valeurs>()
  for (const v of valeurs) parSecteur.set(v.sector ?? "Autre", [...(parSecteur.get(v.sector ?? "Autre") ?? []), v])
  const secteurs = [...parSecteur.entries()].sort((a, b) => a[0].localeCompare(b[0], "fr"))

  return (
    <>
      <PageTitle title="Valeurs">
        {valeurs.length} actions cotées, classées par secteur. Les valeurs sans historique de cours ne sont pas
        surveillées.
      </PageTitle>
      <div className="overflow-x-auto rounded-lg border bg-surface">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="px-4 py-2.5 font-medium">Valeur</th>
              <th className="px-3 py-2.5 font-medium">Symbole</th>
              <th className="px-3 py-2.5 text-right font-medium">Dernier cours</th>
              <th className="px-3 py-2.5 text-right font-medium">Séances</th>
              <th className="px-4 py-2.5 text-right font-medium">Alertes</th>
            </tr>
          </thead>
          {secteurs.map(([secteur, rows]) => (
            <tbody key={secteur} className="tabular">
              <tr className="border-t bg-muted/50">
                <th colSpan={5} className="px-4 py-2 text-left text-xs font-medium text-ink-2">
                  {secteur}
                </th>
              </tr>
              {rows.map((v) => (
                <tr key={v.ticker} className="transition-colors hover:bg-accent/60">
                  <td className="px-4 py-2">
                    {v.n_days > 0 ? (
                      <Link href={`/valeurs/${v.ticker}`} className="font-medium text-ink underline-offset-4 hover:underline">
                        {v.name}
                      </Link>
                    ) : (
                      <span className="text-muted-foreground">{v.name}</span>
                    )}
                    {v.in_masi20 && <span className="ml-2 text-xs text-muted-foreground">MASI 20</span>}
                  </td>
                  <td className="px-3 py-2 text-ink-2">{v.ticker}</td>
                  <td className="px-3 py-2 text-right text-ink">
                    {v.last_close != null ? (
                      <>
                        {num(v.last_close)} <span className="text-xs text-muted-foreground">le {date(v.last_day)}</span>
                      </>
                    ) : (
                      <span className="text-muted-foreground">sans historique</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right text-ink-2">{num(v.n_days, 0)}</td>
                  <td className="px-4 py-2 text-right text-ink-2">{v.n_alerts}</td>
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>
    </>
  )
}
