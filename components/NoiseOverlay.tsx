export function NoiseOverlay() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-10 mix-blend-soft-light"
    >
      <div className="absolute inset-0 opacity-[0.04] bg-[url('data:image/svg+xml,%3Csvg%20xmlns=%22http://www.w3.org/2000/svg%22%20viewBox=%220%200%20160%20160%22%3E%3Cfilter%20id=%22n%22%3E%3CfeTurbulence%20type=%22fractalNoise%22%20baseFrequency=%220.8%22%20numOctaves=%224%22%20stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect%20width=%22100%25%22%20height=%22100%25%22%20filter=%22url(%23n)%22/%3E%3C/svg%3E')]"></div>
      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[length:100%_3px] opacity-[0.06]" />
    </div>
  )
}

