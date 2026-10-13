"use client"

import { MoonIcon, SunIcon } from "lucide-react"
import { useTheme } from "next-themes"

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const dark = resolvedTheme === "dark"
  return (
    <button
      type="button"
      onClick={() => setTheme(dark ? "light" : "dark")}
      className="inline-flex size-9 items-center justify-center rounded-md text-ink-2 transition-colors hover:bg-accent hover:text-ink active:scale-[0.97]"
      aria-label={dark ? "Passer en mode clair" : "Passer en mode sombre"}
      title={dark ? "Mode clair" : "Mode sombre"}
    >
      <SunIcon className="hidden size-[18px] dark:block" strokeWidth={1.75} />
      <MoonIcon className="size-[18px] dark:hidden" strokeWidth={1.75} />
    </button>
  )
}
