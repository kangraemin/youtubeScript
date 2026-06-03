export default function Loading() {
  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      <div className="h-3 w-24 bg-zinc-800/40 rounded animate-pulse mb-4" />
      <div className="aspect-video rounded-xl bg-zinc-800/60 animate-pulse" />
      <div className="mt-6 space-y-3">
        <div className="h-7 w-3/4 bg-zinc-800/60 rounded animate-pulse" />
        <div className="h-4 w-1/2 bg-zinc-800/40 rounded animate-pulse" />
      </div>
      <div className="mt-8 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 bg-zinc-900/40 border border-zinc-800 rounded-lg animate-pulse" />
        ))}
      </div>
    </main>
  )
}
