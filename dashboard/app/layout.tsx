import type { Metadata } from "next"
import { GeistMono } from "geist/font/mono"
import { GeistSans } from "geist/font/sans"
import { SiteFooter } from "@/components/site-footer"
import { SiteHeader } from "@/components/site-header"
import { ThemeProvider } from "@/components/theme-provider"
import { TooltipProvider } from "@/components/ui/tooltip"
import "./globals.css"

export const metadata: Metadata = {
  title: { default: "Surveillance des marchés de Casablanca", template: "%s · Surveillance des marchés" },
  description:
    "Détection des séances atypiques sur les actions cotées à Casablanca et rapprochement avec les publications des émetteurs (AMMC).",
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fr" suppressHydrationWarning className={`${GeistSans.variable} ${GeistMono.variable} antialiased`}>
      <body className="flex min-h-dvh flex-col">
        <ThemeProvider>
          <TooltipProvider>
            <SiteHeader />
            <main className="mx-auto w-full max-w-7xl flex-1 px-4 pt-8 sm:px-6 md:pt-10">{children}</main>
            <SiteFooter />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
