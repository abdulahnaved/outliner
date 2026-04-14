import { jwtVerify } from 'jose'
import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'
import { getAuthSecretKey, SESSION_COOKIE_NAME } from '@/lib/session-token'

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value

  const redirectToLogin = () => {
    const login = new URL('/login', request.url)
    const returnTo = `${pathname}${request.nextUrl.search}`
    login.searchParams.set('next', returnTo)
    return NextResponse.redirect(login)
  }

  const verify = async (): Promise<boolean> => {
    if (!token) return false
    try {
      await jwtVerify(token, getAuthSecretKey())
      return true
    } catch {
      return false
    }
  }

  if (pathname.startsWith('/history') || pathname.startsWith('/dashboard')) {
    if (!(await verify())) return redirectToLogin()
    return NextResponse.next()
  }

  if (pathname === '/login' || pathname === '/register') {
    if (await verify()) {
      return NextResponse.redirect(new URL('/dashboard', request.url))
    }
    return NextResponse.next()
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/history/:path*', '/dashboard', '/dashboard/:path*', '/login', '/register']
}
