export default function Loading() {
  return (
    <main
      className="page-shell"
      aria-busy="true"
      aria-label="요약을 불러오는 중"
    >
      <div className="skeleton skeleton-title" />
      <div className="feed-grid">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="skeleton-card">
            <div className="skeleton skeleton-label" />
            <div className="skeleton skeleton-line" />
            <div className="skeleton skeleton-line" />
            <div className="skeleton skeleton-label" />
          </div>
        ))}
      </div>
    </main>
  )
}
