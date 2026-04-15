import Database from 'better-sqlite3'
import fs from 'fs'
import path from 'path'
import type { Pool } from 'pg'

let db: Database.Database | null = null
let pgPool: Pool | null = null
let pgInitPromise: Promise<void> | null = null

function usingPostgres(): boolean {
  return Boolean(process.env.DATABASE_URL)
}

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

function getSqliteDb(): Database.Database {
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

async function initPostgres(pool: Pool): Promise<void> {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS users (
      id BIGSERIAL PRIMARY KEY,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS saved_scans (
      id BIGSERIAL PRIMARY KEY,
      user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      result_json TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_saved_scans_user_created
      ON saved_scans (user_id, created_at DESC);
  `)
}

async function getPostgresPool(): Promise<Pool> {
  if (pgPool) return pgPool
  const { Pool } = await import('pg')
  pgPool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: process.env.PGSSLMODE === 'disable' ? undefined : { rejectUnauthorized: false }
  })
  if (!pgInitPromise) {
    pgInitPromise = initPostgres(pgPool)
  }
  await pgInitPromise
  return pgPool
}

function pgToSqliteSql(sql: string): string {
  // Convert $1, $2... placeholders to '?' for better-sqlite3
  return sql.replace(/\$\d+/g, '?')
}

export async function dbQuery<T = unknown>(
  sql: string,
  params: unknown[] = []
): Promise<T[]> {
  if (usingPostgres()) {
    const pool = await getPostgresPool()
    const r = await pool.query(sql, params as any[])
    return r.rows as T[]
  }
  const sqlite = getSqliteDb()
  const stmt = sqlite.prepare(pgToSqliteSql(sql))
  return stmt.all(...params) as T[]
}

export async function dbQueryOne<T = unknown>(
  sql: string,
  params: unknown[] = []
): Promise<T | null> {
  const rows = await dbQuery<T>(sql, params)
  return rows[0] ?? null
}

export async function dbExec(
  sql: string,
  params: unknown[] = []
): Promise<{ changes: number; lastInsertId?: number }> {
  if (usingPostgres()) {
    const pool = await getPostgresPool()
    const r = await pool.query(sql, params as any[])
    return { changes: r.rowCount ?? 0 }
  }
  const sqlite = getSqliteDb()
  const stmt = sqlite.prepare(pgToSqliteSql(sql))
  const r = stmt.run(...params)
  return { changes: r.changes, lastInsertId: Number(r.lastInsertRowid) }
}

export async function dbInsertReturningId(
  insertSqlReturningId: string,
  params: unknown[] = []
): Promise<number> {
  if (usingPostgres()) {
    const row = await dbQueryOne<{ id: number }>(insertSqlReturningId, params)
    if (!row || typeof row.id !== 'number') throw new Error('Insert failed (no id returned)')
    return row.id
  }
  // SQLite: ignore RETURNING and use lastInsertRowid
  const sqlite = getSqliteDb()
  const sql = pgToSqliteSql(insertSqlReturningId.replace(/\s+RETURNING\s+id\s*;?\s*$/i, ''))
  const stmt = sqlite.prepare(sql)
  const r = stmt.run(...params)
  return Number(r.lastInsertRowid)
}

// Back-compat: some code still expects getDb() in local mode.
export function getDb(): Database.Database {
  return getSqliteDb()
}
