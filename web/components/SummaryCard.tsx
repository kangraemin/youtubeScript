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

      {summary.macro_views && summary.macro_views.length > 0 && (
        <Section icon="📈" title="거시 진단" color="blue">
          {summary.macro_views.map((it, i) => (
            <ItemCard key={i} accent="blue">
              <ItemHead title={it.topic} speaker={it.speaker} />
              <p className="text-sm text-zinc-300 mt-1 mb-2">{it.view}</p>
              <QuoteList vid={vid} quotes={it.quotes} />
            </ItemCard>
          ))}
        </Section>
      )}

      {summary.chart_levels && summary.chart_levels.length > 0 && (
        <Section icon="📊" title="차트 자리" color="cyan">
          {summary.chart_levels.map((it, i) => (
            <ItemCard key={i} accent="cyan">
              <div className="flex items-baseline gap-2 flex-wrap">
                <span className="text-base font-bold text-white">{it.ticker}</span>
                <span className="text-sm text-cyan-300">{it.level}</span>
                {it.speaker && <span className="text-xs text-zinc-500">— {it.speaker}</span>}
              </div>
              <p className="text-sm text-zinc-300 mt-1 mb-2">{it.reason}</p>
              <QuoteList vid={vid} quotes={it.quotes} />
            </ItemCard>
          ))}
        </Section>
      )}

      {summary.verdicts && summary.verdicts.length > 0 && (
        <Section icon="⚡" title="결론·시그널" color="orange">
          {summary.verdicts.map((it, i) => (
            <ItemCard key={i} accent="orange">
              <div className="text-sm">
                <span className="text-orange-300 font-semibold mr-1">IF</span>
                <span className="text-zinc-200">{it.condition}</span>
              </div>
              <div className="text-sm mt-1">
                <span className="text-orange-300 font-semibold mr-1">→</span>
                <span className="text-zinc-200">{it.consequence}</span>
              </div>
              {it.speaker && <div className="text-xs text-zinc-500 mt-1">— {it.speaker}</div>}
              <div className="mt-2">
                <QuoteList vid={vid} quotes={it.quotes} />
              </div>
            </ItemCard>
          ))}
        </Section>
      )}

      {summary.narrative && (
        <Section icon="📜" title="영상 흐름" color="slate">
          <div className="rounded-lg border border-zinc-800 border-l-[3px] border-l-slate-400 bg-zinc-900/50 p-4">
            <p className="text-sm text-zinc-300 whitespace-pre-line leading-relaxed">
              {summary.narrative}
            </p>
          </div>
        </Section>
      )}

      {summary.lessons && summary.lessons.length > 0 && (
        <Section icon="🎓" title="학습 포인트" color="pink">
          {summary.lessons.map((it, i) => (
            <ItemCard key={i} accent="pink">
              <div className="flex items-baseline gap-2 flex-wrap mb-1">
                <span
                  className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                    lessonTypeBadge[it.type] ?? 'bg-zinc-700 text-zinc-300'
                  }`}
                >
                  {it.type}
                </span>
                {it.speaker && <span className="text-xs text-zinc-500">— {it.speaker}</span>}
              </div>
              <p className="text-sm text-zinc-300 mb-2">{it.lesson}</p>
              <QuoteList vid={vid} quotes={it.quotes} />
            </ItemCard>
          ))}
        </Section>
      )}

      {summary.data_points && summary.data_points.length > 0 && (
        <Section icon="📌" title="통계·숫자" color="zinc">
          {summary.data_points.map((it, i) => (
            <ItemCard key={i} accent="zinc">
              <p className="text-sm text-zinc-100 font-mono mb-2">{it.datum}</p>
              <QuoteList vid={vid} quotes={it.quotes} />
            </ItemCard>
          ))}
        </Section>
      )}

      {summary.action_items && summary.action_items.length > 0 && (
        <Section icon="✅" title="실행 가능" color="teal">
          {summary.action_items.map((it, i) => (
            <ItemCard key={i} accent="teal">
              <div className="flex items-baseline gap-2 flex-wrap">
                <span className="text-sm text-zinc-100">{it.action}</span>
                {it.speaker && <span className="text-xs text-zinc-500">— {it.speaker}</span>}
              </div>
              <div className="mt-2">
                <QuoteList vid={vid} quotes={it.quotes} />
              </div>
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
  blue: 'border-l-blue-400',
  cyan: 'border-l-cyan-400',
  orange: 'border-l-orange-400',
  pink: 'border-l-pink-400',
  zinc: 'border-l-zinc-400',
  teal: 'border-l-teal-400',
  slate: 'border-l-slate-400',
}

const lessonTypeBadge: Record<string, string> = {
  rule: 'bg-blue-500/20 text-blue-300',
  counter: 'bg-red-500/20 text-red-300',
  reference: 'bg-violet-500/20 text-violet-300',
  analogy: 'bg-pink-500/20 text-pink-300',
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
