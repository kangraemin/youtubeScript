export default function Loading() {
  return (
    <main
      className="reader-shell"
      aria-busy="true"
      aria-label="요약을 불러오는 중"
    >
      <div className="skeleton skeleton-label" />
      <div className="skeleton skeleton-title" />
      <div className="skeleton-card">
        <div className="skeleton skeleton-line" />
        <div className="skeleton skeleton-line" />
        <div className="skeleton skeleton-line" />
      </div>
    </main>
  )
}
