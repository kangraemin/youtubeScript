import type { ReadingGuide as Guide } from '@/lib/readingGuide'
import { splitSentences } from './reader/text'
function Points({ items }: { items: string[] }) {
  return (
    <ul className="study-points">
      {items.map((item, i) => {
        const [lead, ...details] = splitSentences(item)
        return (
          <li key={i}>
            <span className="study-point-lead">{lead}</span>
            {details.length > 0 && (
              <ul className="study-point-details">
                {details.map((sentence, j) => <li key={j}>{sentence}</li>)}
              </ul>
            )}
          </li>
        )
      })}
    </ul>
  )
}
export function ReadingGuide({ guide }: { guide: Guide }) {
  return (
    <section
      id="learning"
      className="study-guide reader-section"
      aria-labelledby="learning-heading"
    >
      <header className="study-intro">
        <p className="eyebrow">영상을 읽는 해설</p>
        <h2 id="learning-heading">{guide.title}</h2>
        <Points items={[guide.introduction]} />
      </header>
      <nav className="study-index" aria-label="해설 차례">
        <p>이 글에서 배울 내용</p>
        <ol>
          {guide.topics.map((topic, i) => (
            <li key={topic.id}>
              <a href={`#study-${topic.id}`}>
                <span>{String(i + 1).padStart(2, '0')}</span>
                {topic.title}
              </a>
            </li>
          ))}
        </ol>
      </nav>
      <div className="study-perspectives">
        <h3>화자의 관점부터 잡고 읽기</h3>
        {guide.perspectives.map((p) => (
          <div key={p.name}>
            <h4>{p.name}</h4>
            <Points items={[p.view, p.watch]} />
          </div>
        ))}
      </div>
      {guide.topics.map((topic, i) => (
        <section
          key={topic.id}
          id={`study-${topic.id}`}
          className="study-topic"
        >
          <div className="study-kicker">
            <span>주제 {String(i + 1).padStart(2, '0')}</span>
            <span>
              {topic.speaker} · 자막 {topic.ts}
            </span>
          </div>
          <h3>{topic.title}</h3>
          <Points items={topic.points} />
          {topic.background.length > 0 && (
            <aside className="study-background">
              <h4>
                이해를 돕는 배경지식 <span>보충 설명</span>
              </h4>
              <Points items={topic.background} />
            </aside>
          )}
          <div className="study-takeaway">
            <h4>여기서 배울 점</h4>
            <Points items={topic.takeaways} />
          </div>
          {!!topic.caveats?.length && (
            <div className="study-caveats">
              <h4>구분해서 볼 부분</h4>
              <Points items={topic.caveats} />
            </div>
          )}
        </section>
      ))}
      <section className="study-topic">
        <h3>다른 영상을 볼 때도 가져갈 질문</h3>
        <Points items={guide.lessons} />
      </section>
      <footer className="study-sources">
        <h3>배경설명 참고 자료</h3>
        <ul>
          {guide.sources.map((source) => (
            <li key={source.url}>
              <a href={source.url} target="_blank" rel="noreferrer">
                {source.label} ↗
              </a>
            </li>
          ))}
        </ul>
        <p>{guide.coverage.note}</p>
        <p>경제 학습과 무관한 부분: {guide.coverage.excluded}</p>
      </footer>
    </section>
  )
}
