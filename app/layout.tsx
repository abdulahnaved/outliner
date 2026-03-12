import type { Metadata } from 'next'
import { JetBrains_Mono } from 'next/font/google'
import './globals.css'
import { Navbar } from '../components/Navbar'
import { Footer } from '../components/Footer'
import { NoiseOverlay } from '../components/NoiseOverlay'

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap'
})

export const metadata: Metadata = {
  title: 'outliner — surface tells a story',
  description: 'A calm, structured view of what your website exposes.'
}

export default function RootLayout(props: { children: React.ReactNode }) {
  return (
    <html lang="en" className={jetbrains.variable}>
      <body className="min-h-screen bg-bg font-mono text-text">
        <NoiseOverlay />
        <Navbar />
        <div className="pt-[72px]">
          <main className="mx-auto max-w-5xl px-4 py-10">{props.children}</main>
        </div>
        <Footer />
      </body>
    </html>
  )
}

