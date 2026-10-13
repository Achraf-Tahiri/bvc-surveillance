"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"

const LINKS = [
  { href: "/", label: "Séance" },
  { href: "/alertes", label: "Alertes" },
  { href: "/valeurs", label: "Valeurs" },
  { href: "/etude", label: "Étude d'événements" },
  { href: "/methode", label: "Méthode" },
]

export function NavLinks() {
  const path = usePathname()
  return (
    <nav className="-mx-1 flex items-center gap-0.5 overflow-x-auto text-sm" aria-label="Navigation principale">
      {LINKS.map((l) => {
        const active = l.href === "/" ? path === "/" : path.startsWith(l.href)
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "whitespace-nowrap rounded-md px-2.5 py-1.5 text-ink-2 transition-colors hover:bg-accent hover:text-ink",
              active && "bg-accent font-medium text-ink",
            )}
          >
            {l.label}
          </Link>
        )
      })}
    </nav>
  )
}
