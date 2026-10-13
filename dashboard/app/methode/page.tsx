import type { Metadata } from "next"
import { PageTitle, Prose, Section } from "@/components/bits"
import { ProfileChart } from "@/components/charts/profile-chart"
import { num } from "@/lib/format"
import { detection, validationTest } from "@/lib/resultats"

export const metadata: Metadata = { title: "Méthode et limites" }

const DETECTEURS = [
  { key: "alertes (Isolation Forest ou |z| > 4)", label: "Alertes (Isolation Forest ou règle)" },
  { key: "Isolation Forest", label: "Isolation Forest seul" },
  { key: "règle |z| > 4", label: "Règle |z| > 4 seule" },
]

export default function MethodePage() {
  const v = validationTest(DETECTEURS[0].key)
  const per = Object.fromEntries(detection.periodes.map((p) => [p.periode, p]))
  const prof = detection.profil

  return (
    <>
      <PageTitle title="Méthode et limites">
        Ce qui est mesuré, comment la détection a été validée, et ce que ces chiffres ne disent pas.
      </PageTitle>

      <Section title="Données" className="mt-0">
        <Prose>
          <p>
            Cours quotidiens de 77 actions et des indices de 2012 à mars 2026 (jeu de données public Kaggle issu de
            TradingView, ajusté des divisions de titres), puis collecte automatique après chaque séance depuis le 13 octobre
            2026 sur le site public de la Bourse de Casablanca (ouverture, plus haut, plus bas, clôture, titres échangés). Les
            mois d&apos;avril à octobre 2026 manquent. Publications des émetteurs : 9 935 communiqués de l&apos;AMMC (2010
            à 2026), rattachés à une valeur et classés par type par des règles vérifiées à la main (98,0 % de classements
            justes sur un échantillon de 200 publications jamais utilisé pour régler les règles).
          </p>
        </Prose>
      </Section>

      <Section title="Détection des séances atypiques">
        <Prose>
          <p>Pour chaque valeur et chaque séance échangée, cinq variables calculées sans regarder l&apos;avenir :</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>z : rendement anormal du jour par rapport au MASI, divisé par son écart type habituel ;</li>
            <li>volume anormal : écart à la médiane des 250 séances précédentes, en écarts robustes ;</li>
            <li>ratio de volatilité entre les 20 et les 250 dernières séances ;</li>
            <li>rang du mouvement parmi les valeurs échangées le même jour ;</li>
            <li>part des 20 dernières séances où la valeur a été échangée.</li>
          </ul>
          <p>
            Un Isolation Forest est entraîné sur 2013 à 2022 ({num(per.entrainement.observations, 0)} observations). Le seuil
            retient le 1 % des observations d&apos;entraînement les plus isolées. La règle |z| &gt; 4 complète le modèle.
            Variables et seuils ont été choisis sur 2013 à 2022 seulement, avant de regarder la période de test. Chaque
            soir, le robot recalcule les variables, applique le même modèle (même graine) et met à jour les alertes.
          </p>
          <p>
            Chaque alerte est rapprochée des publications de la valeur : <strong className="text-ink">expliquée</strong> si
            une publication tombe à une séance près, <strong className="text-ink">précède une publication</strong> si elle
            tombe 2 à 10 séances après, <strong className="text-ink">sans explication</strong> sinon.
          </p>
        </Prose>
      </Section>

      <Section title="Validation hors période (2023 à mars 2026)">
        <Prose>
          <p>
            Question : les alertes tombent-elles plus souvent près d&apos;une publication que des séances prises au hasard
            dans les mêmes valeurs ? Le gain est le rapport des deux fréquences ; l&apos;intervalle de confiance vient
            d&apos;un bootstrap en grappes de dates. Sur {num(per.test.observations, 0)} observations de test,{" "}
            {v.alertes} alertes.
          </p>
        </Prose>
        <div className="mt-4 overflow-x-auto rounded-lg border bg-surface">
          <table className="w-full min-w-[680px] text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                <th className="px-4 py-2.5 font-medium">Détecteur</th>
                <th className="px-3 py-2.5 font-medium">Publications</th>
                <th className="px-3 py-2.5 text-right font-medium">Alertes</th>
                <th className="px-3 py-2.5 text-right font-medium">Proches d&apos;une publication</th>
                <th className="px-3 py-2.5 text-right font-medium">Au hasard</th>
                <th className="px-4 py-2.5 text-right font-medium">Gain (IC 95 %)</th>
              </tr>
            </thead>
            <tbody className="divide-y tabular">
              {["toutes", "résultats et profit warnings"].flatMap((pubs) =>
                DETECTEURS.map((d) => {
                  const r = validationTest(d.key, pubs)
                  const sig = r.gain_ic_bas > 1
                  return (
                    <tr key={pubs + d.key}>
                      <td className="px-4 py-2 text-ink">{d.label}</td>
                      <td className="px-3 py-2 text-ink-2">{pubs === "toutes" ? "Toutes" : "Résultats et profit warnings"}</td>
                      <td className="px-3 py-2 text-right text-ink-2">{r.alertes}</td>
                      <td className="px-3 py-2 text-right text-ink-2">{num(r.part_proche_pct, 1)} %</td>
                      <td className="px-3 py-2 text-right text-ink-2">{num(r.part_hasard_pct, 1)} %</td>
                      <td className="px-4 py-2 text-right">
                        <span className={sig ? "font-semibold text-ink" : "text-ink-2"}>×{num(r.gain, 2)}</span>{" "}
                        <span className="text-xs text-muted-foreground">
                          ({num(r.gain_ic_bas, 2)} à {num(r.gain_ic_haut, 2)})
                        </span>
                      </td>
                    </tr>
                  )
                }),
              )}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          « Proche » : publication de la valeur dont le jour de réaction tombe entre la séance précédente et la séance
          suivante. En gras : intervalle entièrement au-dessus de 1.
        </p>

        <div className="mt-6 rounded-lg border bg-surface p-4">
          <ProfileChart
            x={prof.map((p) => p.k)}
            series={[
              { name: "Séances d'alerte", color: "var(--brand)", y: prof.map((p) => p.alertes_pct), kind: "bar" },
              { name: "Séances au hasard, mêmes valeurs", color: "var(--ink-2)", y: prof.map((p) => p.hasard_pct) },
            ]}
            format="pct1"
            xLabel="k : séances entre l'alerte et le jour de réaction de la publication"
            yLabel="Part avec une publication de la valeur à la séance d+k"
          />
        </div>
      </Section>

      <Section title="Limites">
        <Prose>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>
              Le gain est modeste : la plupart des grands mouvements ne coïncident avec aucune publication de l&apos;AMMC, et la
              plupart des publications ne font pas bouger les cours. L&apos;Isolation Forest seul ne fait pas mieux que le
              hasard de façon nette sur la période de test ; la règle sur le rendement anormal porte l&apos;essentiel du
              signal.
            </li>
            <li>
              Les publications de l&apos;AMMC ne sont qu&apos;une source d&apos;information parmi d&apos;autres (presse, sites
              des émetteurs). Une alerte « sans explication » peut avoir une cause publique non couverte ici.
            </li>
            <li>
              Sur les valeurs peu liquides, quelques transactions suffisent à produire un mouvement de plus de 8 % suivi
              d&apos;un retour : ces allers-retours sont de vraies transactions et peuvent déclencher des alertes.
            </li>
            <li>
              Avant 2020, l&apos;AMMC ne donne que la date des publications, pas l&apos;heure : le jour de réaction est moins
              précis. La couverture des publications est aussi plus faible avant 2019.
            </li>
            <li>
              Les cours collectés en direct ne sont pas ajustés des divisions de titres, et les mois d&apos;avril à octobre
              2026 manquent : la première séance collectée n&apos;a pas de rendement calculable.
            </li>
            <li>Une alerte est un signal statistique. Elle ne constitue en aucun cas une accusation contre un émetteur.</li>
          </ul>
        </Prose>
      </Section>
    </>
  )
}
