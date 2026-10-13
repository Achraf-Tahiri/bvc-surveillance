import "server-only"
import postgres from "postgres"

// Compte en lecture seule (GRANT SELECT uniquement). L'adresse reste côté serveur :
// elle n'est jamais envoyée au navigateur.
const url = process.env.DATABASE_URL_LECTURE

export const sql = url
  ? postgres(url, { max: 3, prepare: false, idle_timeout: 20, connect_timeout: 15 })
  : null

export function db() {
  if (!sql) throw new Error("DATABASE_URL_LECTURE non défini (voir dashboard/.env.example)")
  return sql
}
