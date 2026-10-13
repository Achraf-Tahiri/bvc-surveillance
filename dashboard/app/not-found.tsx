import Link from "next/link"

export default function NotFound() {
  return (
    <div className="py-24">
      <h1 className="text-2xl font-semibold tracking-tight text-ink">Page introuvable</h1>
      <p className="mt-2 text-ink-2">Cette valeur ou cette page n&apos;existe pas.</p>
      <Link href="/valeurs" className="mt-4 inline-block text-primary underline-offset-4 hover:underline">
        Voir la liste des valeurs
      </Link>
    </div>
  )
}
