export default function Loading() {
  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <div className="h-8 w-44 bg-zinc-800/60 rounded animate-pulse mb-8" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="rounded-xl border border-zinc-800 bg-zinc-900/40 overflow-hidden"
          >
            <div className="aspect-video bg-zinc-800/60 animate-pulse" />
            <div className="p-3 space-y-2">
              <div className="h-4 bg-zinc-800/60 rounded animate-pulse" />
              <div className="h-3 w-2/3 bg-zinc-800/40 rounded animate-pulse" />
              <div className="h-3 w-1/3 bg-zinc-800/30 rounded animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    </main>
  )
}
