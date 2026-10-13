import Link from "next/link"
import { CATEGORIES } from "@/lib/format"
import type { Categorie } from "@/lib/types"
import { cn } from "@/lib/utils"

export function CategoryBadge({ categorie, className }: { categorie: Categorie; className?: string }) {
  const c = CATEGORIES[categorie]
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap text-[13px] text-ink-2", className)}>
      <span className="size-2 shrink-0 rounded-full" style={{ background: c.color }} aria-hidden />
      {c.label}
    </span>
  )
}

export function Stat({
  label,
  value,
  delta,
  deltaTone,
  note,
}: {
  label: string
  value: string
  delta?: string
  deltaTone?: "up" | "down" | "flat"
  note?: string
}) {
  return (
    <div className="flex flex-col gap-1 py-1">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-semibold tracking-tight text-ink">{value}</span>
        {delta && (
          <span
            className={cn(
              "text-sm font-medium tabular",
              deltaTone === "up" && "text-up",
              deltaTone === "down" && "text-down",
              deltaTone === "flat" && "text-ink-2",
            )}
          >
            {delta}
          </span>
        )}
      </div>
      {note && <div className="text-xs text-muted-foreground">{note}</div>}
    </div>
  )
}

export function PageTitle({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="mb-8 max-w-[75ch]">
      <h1 className="text-3xl font-semibold tracking-tight text-ink md:text-4xl">{title}</h1>
      {children && <div className="mt-3 text-base leading-relaxed text-ink-2">{children}</div>}
    </div>
  )
}

export function Section({
  title,
  children,
  aside,
  className,
}: {
  title: string
  children: React.ReactNode
  aside?: React.ReactNode
  className?: string
}) {
  return (
    <section className={cn("mt-12", className)}>
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold tracking-tight text-ink">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  )
}

export function MoreLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="text-sm text-primary underline-offset-4 hover:underline">
      {children}
    </Link>
  )
}

export function Prose({ children }: { children: React.ReactNode }) {
  return <div className="max-w-[72ch] space-y-3 text-[15px] leading-relaxed text-ink-2">{children}</div>
}
