export function SiteFooter() {
  return (
    <footer className="mt-20 border-t">
      <div className="mx-auto grid max-w-7xl gap-4 px-4 py-8 text-sm text-muted-foreground sm:px-6 md:grid-cols-[1fr_auto]">
        <p className="max-w-[70ch] leading-relaxed">
          Projet personnel, non affilié à la Bourse de Casablanca ni à l&apos;AMMC. Données publiques.
          Une alerte est un signal statistique, pas une accusation.
        </p>
        <div className="flex flex-wrap gap-x-5 gap-y-1 md:justify-end">
          <a className="underline-offset-4 hover:text-ink hover:underline" href="https://github.com/Achraf-Tahiri/bvc-surveillance">
            Code source
          </a>
          <span>
            Graphiques de cours :{" "}
            <a className="underline-offset-4 hover:text-ink hover:underline" href="https://www.tradingview.com/">
              TradingView Lightweight Charts
            </a>
          </span>
        </div>
      </div>
    </footer>
  )
}
