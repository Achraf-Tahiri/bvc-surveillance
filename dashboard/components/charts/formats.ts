import { num, pct, signed } from "@/lib/format"

// Les fonctions ne passent pas des composants serveur aux composants client :
// les graphiques reçoivent le nom du format.
export const FORMATS = {
  ratio1: (v: number) => num(v, 1),
  ratio2: (v: number) => num(v, 2),
  num1: (v: number) => signed(v, 1),
  pct0: (v: number) => num(v, 0) + " %",
  pct1: (v: number) => num(v, 1) + " %",
  pctSigned1: (v: number) => pct(v, 1),
} as const

export type Fmt = keyof typeof FORMATS
