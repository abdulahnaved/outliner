import type { Pool } from 'pg'

let pgPool: Pool | null = null
let pgInitPromise: Promise<void> | null = null

function requireDatabaseUrl(): string {
  const url = process.env.DATABASE_URL
  if (!url) {
    throw new Error('DATABASE_URL must be set (Neon Postgres) to use auth and saved scans.')
  }
  return url
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
    connectionString: requireDatabaseUrl(),
    ssl: process.env.PGSSLMODE === 'disable' ? undefined : { rejectUnauthorized: false },
    // Serverless-friendly defaults: keep the pool tiny and fail fast.
    max: 1,
    idleTimeoutMillis: 10_000,
    connectionTimeoutMillis: 5_000,
    allowExitOnIdle: true
  })
  if (!pgInitPromise) {
    pgInitPromise = initPostgres(pgPool)
  }
  await pgInitPromise
  return pgPool
}

export async function dbQuery<T = unknown>(
  sql: string,
  params: unknown[] = []
): Promise<T[]> {
  const pool = await getPostgresPool()
  const r = await pool.query(sql, params as any[])
  return r.rows as T[]
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
  const pool = await getPostgresPool()
  const r = await pool.query(sql, params as any[])
  return { changes: r.rowCount ?? 0 }
}

export async function dbInsertReturningId(
  insertSqlReturningId: string,
  params: unknown[] = []
): Promise<number> {
  const row = await dbQueryOne<{ id: unknown }>(insertSqlReturningId, params)
  const raw = row ? (row as any).id : undefined
  const n = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw) : NaN
  if (!Number.isFinite(n) || n < 1) throw new Error('Insert failed (no id returned)')
  return Math.trunc(n)
}
