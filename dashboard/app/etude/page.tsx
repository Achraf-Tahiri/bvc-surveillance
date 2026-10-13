import type { Metadata } from "next"
import { PageTitle, Prose, Section, Stat } from "@/components/bits"
import { BarsCI } from "@/components/charts/bars-ci"
import { ProfileChart } from "@/components/charts/profile-chart"
import { date, num, pct, signed } from "@/lib/format"
import { etude } from "@/lib/resultats"

export const metadata: Metadata = { title: "Étude d'événements" }

export default function EtudePage() {
  const t = Object.fromEntries(etude.par_type.map((r) => [r.event_type, r]))
  const res = t.resultats
  const pw = t.profit_warning
  const placebo = t.placebo
  const types = etude.par_type.filter((r) => r.event_type !== "placebo").sort((a, b) => (b.vr_ann ?? 0) - (a.vr_ann ?? 0))
  const iso = Object.fromEntries(etude.par_type_isoles.map((r) => [r.event_type, r]))
  const pv = etude.profil_variance
  const pwp = etude.profit_warnings

  return (
    <>
      <PageTitle title="Étude d'événements">
        Comment les cours réagissent-ils aux publications des émetteurs ? {num(etude.evenements, 0)} publications AMMC
        étudiées du {date(etude.periode[0])} au {date(etude.periode[1])}, dont {num(etude.evenements_liquides, 0)} sur{" "}
        {etude.valeurs_liquides} valeurs liquides (cours sur plus de 90 % des séances), qui forment l&apos;étude principale.
      </PageTitle>

      <div className="grid grid-cols-2 gap-x-6 gap-y-4 border-y py-5 md:grid-cols-4">
        <Stat label="Variance autour des résultats" value={`×${num(res.vr_ann, 2)}`} note={`IC ${num(res.vr_ann_ic_bas, 2)} à ${num(res.vr_ann_ic_haut, 2)}, n = ${res.n}`} />
        <Stat
          label="Volume autour des résultats"
          value={`×${num(Math.exp(res.volume_anormal_ann ?? 0), 1)}`}
          note={`log du volume +${num(res.volume_anormal_ann, 2)}`}
        />
        <Stat
          label="Profit warnings, séances 0 et +1"
          value={pct(pw.car_ann_pct, 1)}
          note={`IC ${pct(pw.car_ann_ic_bas, 1)} à ${pct(pw.car_ann_ic_haut, 1)}, n = ${pw.n}`}
        />
        <Stat label="Dates sans publication" value={`×${num(placebo.vr_ann, 2)}`} note="placebo : calibration correcte" />
      </div>

      <Section title="Intensité de la réaction par type de publication">
        <Prose>
          <p>
            Sans prévision d&apos;analystes, le signe d&apos;une annonce de résultats est inconnu. On mesure donc
            l&apos;intensité de la réaction : le rapport entre la variance du rendement anormal sur les séances 0 et +1 et sa
            variance habituelle (1 = séance ordinaire).
          </p>
        </Prose>
        <div className="mt-4 rounded-lg border bg-surface p-4">
          <BarsCI
            rows={types.map((r) => ({ label: r.nom, value: r.vr_ann ?? 0, lo: r.vr_ann_ic_bas, hi: r.vr_ann_ic_haut, n: r.n }))}
            format="ratio1"
            reference={{ value: placebo.vr_ann ?? 1, label: "dates sans publication" }}
            axisLabel="Rapport de variance sur les séances 0 et +1"
          />
        </div>
      </Section>

      <Section title="Profil de la réaction séance par séance">
        <Prose>
          <p>
            Événements isolés (aucune autre publication de la valeur à dix séances près). La réaction est concentrée sur
            les séances 0 et +1 ; rien de notable avant la publication des résultats.
          </p>
        </Prose>
        <div className="mt-4 rounded-lg border bg-surface p-4">
          <ProfileChart
            x={etude.jours}
            series={[
              { name: `Résultats (n = ${pv.resultats.n})`, color: "var(--cat-expliquee)", y: pv.resultats.y },
              { name: `Indicateurs trimestriels (n = ${pv.indicateurs_trimestriels.n})`, color: "var(--cat-precede)", y: pv.indicateurs_trimestriels.y },
              { name: `Dates sans publication (n = ${pv.placebo.n})`, color: "var(--faint)", y: pv.placebo.y, dashed: true },
            ]}
            format="ratio1"
            xLabel="Séances autour de la publication (0 = jour de réaction)"
            yLabel="Variance anormale moyenne (1 = séance ordinaire)"
            highlight={[0, 1]}
          />
        </div>
      </Section>

      <Section title="Profit warnings : rendement anormal cumulé">
        <Prose>
          <p>
            Baisse moyenne de {num(Math.abs(pw.car_ann_pct ?? 0), 1)} % en deux séances, sans rebond ensuite. Avant
            l&apos;annonce, le volume est déjà élevé sur les profit warnings isolés (log du volume{" "}
            {signed(iso.profit_warning?.volume_anormal_pre, 2)}, IC{" "}
            {num(iso.profit_warning?.volume_anormal_pre_ic_bas, 2)} à {num(iso.profit_warning?.volume_anormal_pre_ic_haut, 2)},{" "}
            {iso.profit_warning?.n} événements sur {iso.profit_warning?.valeurs} valeurs) : un signal statistique, à
            interpréter avec prudence vu la taille de l&apos;échantillon.
          </p>
        </Prose>
        <div className="mt-4 rounded-lg border bg-surface p-4">
          <ProfileChart
            x={etude.jours}
            series={[
              {
                name: `Profit warnings (n = ${pwp.profit_warning.n}), IC 95 %`,
                color: "var(--cat-expliquee)",
                y: pwp.profit_warning.y,
                lo: pwp.profit_warning.bas,
                hi: pwp.profit_warning.haut,
              },
              { name: `Dates sans publication (n = ${pwp.placebo.n})`, color: "var(--faint)", y: pwp.placebo.y, dashed: true },
            ]}
            format="pctSigned1"
            xLabel="Séances autour de la publication (0 = jour de réaction)"
            yLabel="Rendement anormal cumulé depuis la séance -10"
            zero
          />
        </div>
      </Section>

      <div className="grid gap-x-10 lg:grid-cols-2 [&>*]:min-w-0">
        <Section title="Résultats, par groupe de secteurs">
          <div className="rounded-lg border bg-surface p-4">
            <BarsCI
              rows={[...etude.resultats_par_secteur]
                .sort((a, b) => (b.vr_ann ?? 0) - (a.vr_ann ?? 0))
                .map((r) => ({ label: r.sector_group, value: r.vr_ann ?? 0, lo: r.vr_ann_ic_bas, hi: r.vr_ann_ic_haut, n: r.n }))}
              format="ratio1"
              reference={{ value: 1, label: "séance ordinaire" }}
              axisLabel="Rapport de variance, publications de résultats"
            />
          </div>
        </Section>
        <Section title="Résultats, par année">
          <div className="rounded-lg border bg-surface p-4">
            <BarsCI
              rows={etude.resultats_par_annee.map((r) => ({
                label: String(r.year),
                value: r.vr_ann ?? 0,
                lo: r.vr_ann_ic_bas,
                hi: r.vr_ann_ic_haut,
                n: r.n,
              }))}
              format="ratio1"
              reference={{ value: 1, label: "séance ordinaire" }}
              axisLabel="Rapport de variance, publications de résultats"
            />
          </div>
        </Section>
      </div>

      <Section title="Méthode en bref">
        <Prose>
          <p>
            Modèle de marché sur le MASI (rendements logarithmiques) estimé sur les séances −250 à −30 avec au moins 150
            séances échangées. Le jour 0 est la séance de la publication en heure de Casablanca ; une publication après la
            clôture de 15h30 compte pour la séance suivante. Intervalles de confiance à 95 % par bootstrap en grappes de
            dates (les résultats tombent souvent le même jour). Les dates sans publication servent de référence.
          </p>
        </Prose>
      </Section>
    </>
  )
}
