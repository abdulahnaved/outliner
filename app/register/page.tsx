import { redirect } from 'next/navigation'

/** Old URL: forwards to unified account page */
export default function RegisterPage({
  searchParams
}: {
  searchParams: { next?: string | string[] }
}) {
  const qs = new URLSearchParams()
  qs.set('mode', 'register')
  const n = searchParams.next
  if (typeof n === 'string' && n) qs.set('next', n)
  redirect(`/login?${qs.toString()}`)
}
