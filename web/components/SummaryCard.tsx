import { Summary } from '@/lib/supabase'
import { QuoteList } from './QuoteList'

type Props = { vid: string; summary: Summary | null }

export function SummaryCard({ vid, summary }: Props) {
  if (!summary) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6 text-center text-zinc-500">
        아직 요약되지 않았어요. /loop이 처리 중입니다.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {summary.headline && (
        <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 p-4">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-sky-400 mb-1">
            📝 HEADLINE
          </div>
          <div className="text-base font-semibold leading-relaxed">{summary.headline}</div>
        </div>
      )}

      {summary.buys && summary.buys.length > 0 && (
        <Section icon="💰" title="매수" color="green">
          {summary.buys.map((it, i) => (
            <ItemCard key={i} accent="green">
              <ItemHead title={it.ticker} speaker={it.speaker} />
              <p className="text-sm text-zinc-300 mt-1 mb-2">{it.reason}</p>
              <QuoteList vid={vid} quotes={it.quotes} />
            </ItemCard>
          ))}
        </Section>
      )}

      {summary.sells && summary.sells.length > 0 && (
        <Section icon="🔻" title="매도/손절" color="red">
          {summary.sells.map((it, i) => (
            <ItemCard key={i} accent="red">
              <ItemHead title={it.ticker} speaker={it.speaker} />
              <p className="text-sm text-zinc-300 mt-1 mb-2">{it.reason}</p>
              <QuoteList vid={vid} quotes={it.quotes} />
            </ItemCard>
          ))}
        </Section>
      )}

      {summary.watchlist && summary.watchlist.length > 0 && (
        <Section icon="👀" title="봐야 할 것" color="amber">
          {summary.watchlist.map((it, i) => (
            <ItemCard key={i} accent="amber">
              <ItemHead title={it.topic} speaker={it.speaker} />
              <p className="text-sm text-zinc-300 mt-1 mb-2">{it.reason}</p>
              <QuoteList vid={vid} quotes={it.quotes} />
            </ItemCard>
          ))}
        </Section>
      )}

      {summary.terms && summary.terms.length > 0 && (
        <Section icon="📖" title="용어" color="violet">
          {summary.terms.map((it, i) => (
            <ItemCard key={i} accent="violet">
              <div className="text-base font-bold text-violet-400">{it.term}</div>
              <p className="text-sm text-zinc-300 mt-1 mb-2">{it.explain}</p>
              {it.context && <p className="text-xs text-zinc-500 italic">{it.context}</p>}
              <QuoteList vid={vid} quotes={it.quotes} />
            </ItemCard>
          ))}
        </Section>
      )}
    </div>
  )
}

function Section({
  icon, title, color, children,
}: { icon: string; title: string; color: string; children: React.ReactNode }) {
  return (
    <section>
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-zinc-800">
        <span className="text-lg">{icon}</span>
        <h2 className="text-base font-bold">{title}</h2>
      </div>
      <div className="space-y-2">{children}</div>
    </section>
  )
}

const accentBorder: Record<string, string> = {
  green: 'border-l-emerald-400',
  red: 'border-l-red-400',
  amber: 'border-l-amber-400',
  violet: 'border-l-violet-400',
}

function ItemCard({ accent, children }: { accent: string; children: React.ReactNode }) {
  return (
    <div className={`rounded-lg border border-zinc-800 border-l-[3px] ${accentBorder[accent]} bg-zinc-900/50 p-4`}>
      {children}
    </div>
  )
}

function ItemHead({ title, speaker }: { title: string; speaker: string | null }) {
  return (
    <div className="flex items-baseline gap-2 flex-wrap">
      <span className="text-base font-bold text-white">{title}</span>
      {speaker && <span className="text-xs text-zinc-500">— {speaker}</span>}
    </div>
  )
}
