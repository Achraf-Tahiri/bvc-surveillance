import "server-only"
import detection from "@/data/detection.json"
import etude from "@/data/etude.json"

export { detection, etude }

export type Validation = (typeof detection.validation)[number]

export function validationTest(detecteur: string, publications = "toutes", fenetre = "[d-1, d+1]") {
  return detection.validation.find(
    (v) => v.periode === "test" && v.detecteur === detecteur && v.publications === publications && v.fenetre === fenetre,
  )!
}
