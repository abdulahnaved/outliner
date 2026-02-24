export function normalizeDomain(input: string): string | null {
  const trimmed = input.trim()
  if (!trimmed) return null

  let url: URL
  try {
    if (/^https?:\/\//i.test(trimmed)) {
      url = new URL(trimmed)
    } else {
      url = new URL(`https://${trimmed}`)
    }
  } catch {
    return null
  }

  let hostname = url.hostname.toLowerCase()
  if (hostname.startsWith('www.')) {
    hostname = hostname.slice(4)
  }

  if (!/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(hostname)) {
    return null
  }

  return hostname
}

