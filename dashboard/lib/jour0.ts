// Même règle que bvcsurv.etude.event_day : heure de Casablanca, publication après la
// clôture (15h30) ou un jour sans séance -> séance suivante ; avant 2020 l'AMMC ne
// donne que la date (horodatage à minuit UTC pile).
const CLOSE_MIN = 15 * 60 + 30
const MAX_LAG_DAYS = 7
const parts = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Africa/Casablanca",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
})

function addDay(iso: string) {
  const d = new Date(iso + "T00:00:00Z")
  d.setUTCDate(d.getUTCDate() + 1)
  return d.toISOString().slice(0, 10)
}

export function jourReaction(publishedAt: string, days: string[]): string | null {
  const ts = new Date(publishedAt)
  let day: string
  if (ts.getUTCHours() === 0 && ts.getUTCMinutes() === 0 && ts.getUTCSeconds() === 0) {
    day = publishedAt.slice(0, 10)
  } else {
    const p = Object.fromEntries(parts.formatToParts(ts).map((x) => [x.type, x.value]))
    day = `${p.year}-${p.month}-${p.day}`
    if (Number(p.hour) * 60 + Number(p.minute) > CLOSE_MIN) day = addDay(day)
  }
  let lo = 0
  let hi = days.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (days[mid] < day) lo = mid + 1
    else hi = mid
  }
  if (lo >= days.length) return null
  const lag = (Date.parse(days[lo]) - Date.parse(publishedAt.slice(0, 10))) / 86400000
  return lag <= MAX_LAG_DAYS ? days[lo] : null
}
