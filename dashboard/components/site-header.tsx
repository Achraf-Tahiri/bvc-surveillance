import Link from "next/link"
import { NavLinks } from "./nav-links"
import { ThemeToggle } from "./theme-toggle"

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/75">
      <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-3 sm:px-6 md:h-16 md:flex-row md:items-center md:gap-8 md:py-0">
        <div className="flex items-center justify-between gap-4">
          <Link href="/" className="flex items-baseline gap-2 font-semibold tracking-tight text-ink">
            <span className="text-[15px]">Surveillance des marchés</span>
            <span className="text-sm font-normal text-faint">Casablanca</span>
          </Link>
          <div className="md:hidden">
            <ThemeToggle />
          </div>
        </div>
        <NavLinks />
        <div className="ml-auto hidden md:block">
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
