import Database from 'better-sqlite3'
import fs from 'fs'
import path from 'path'

let db: Database.Database | null = null

function resolveDbPath(): string {
  const env = process.env.OUTLINER_DATABASE_PATH
  if (env) return env
  // In serverless environments (e.g. Vercel), the project filesystem may be read-only.
  // Use /tmp to keep auth endpoints functional (note: not durable storage).
  if (process.env.VERCEL) {
    return '/tmp/outliner.db'
  }
  const dir = path.join(process.cwd(), 'data')
  try {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
    return path.join(dir, 'outliner.db')
  } catch {
    return '/tmp/outliner.db'
  }
}

export function getDb(): Database.Database {
  if (db) return db
  const file = resolveDbPath()
  db = new Database(file)
  db.pragma('journal_mode = WAL')
  initSchema(db)
  return db
}

function initSchema(database: Database.Database): void {
  database.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT NOT NULL UNIQUE COLLATE NOCASE,
      password_hash TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS saved_scans (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      result_json TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_saved_scans_user_created ON saved_scans (user_id, created_at DESC);
  `)
}
