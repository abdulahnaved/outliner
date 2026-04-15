import { NextResponse } from 'next/server'

export const runtime = 'nodejs'

export async function GET() {
  const hasDb = !!process.env.DATABASE_URL
  const secretLen = (process.env.OUTLINER_AUTH_SECRET ?? '').length
  const hasSecret = secretLen >= 16

  return NextResponse.json(
    {
      ok: true,
      now: new Date().toISOString(),
      nodeEnv: process.env.NODE_ENV ?? null,
      vercelEnv: process.env.VERCEL_ENV ?? null,
      hasDatabaseUrl: hasDb,
      hasAuthSecret: hasSecret,
      authSecretLength: secretLen
    },
    { status: 200 }
  )
}

