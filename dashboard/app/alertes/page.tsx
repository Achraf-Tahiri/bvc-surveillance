import type { Metadata } from "next"
import { AlertsTable } from "@/components/alerts-table"
import { MoreLink, PageTitle } from "@/components/bits"
import { getAlerts } from "@/lib/data"

export const metadata: Metadata = { title: "Alertes" }

export default async function AlertesPage() {
  const alertes = await getAlerts()
  return (
    <>
      <PageTitle title="Alertes">
        Séances atypiques détectées sur chaque valeur depuis 2013, avec la publication de l&apos;émetteur la plus proche.
        Une alerte est un signal statistique : un mouvement qui précède une publication n&apos;est pas une accusation.{" "}
        <MoreLink href="/methode">Comment sont-elles calculées ?</MoreLink>
      </PageTitle>
      <AlertsTable alertes={alertes} />
    </>
  )
}
