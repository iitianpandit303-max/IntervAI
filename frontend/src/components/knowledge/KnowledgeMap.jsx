function confidenceLabel(confidence = 0) {
  if (confidence >= 0.75) return 'high evidence'
  if (confidence >= 0.4) return 'growing evidence'
  if (confidence > 0) return 'profile prior'
  return 'not tested'
}

function sortedTopics(map) {
  if (!map?.topics) return []
  return Object.values(map.topics).sort((a, b) => (b.score || 0) - (a.score || 0))
}

export default function KnowledgeMap({ map, compact = false }) {
  const topics = sortedTopics(map)

  if (!topics.length) {
    return (
      <section className={`knowledge-map ${compact ? 'knowledge-map--compact' : ''}`}>
        <div className="knowledge-map__header">
          <div>
            <span className="section-kicker">Candidate knowledge map</span>
            <h2>{compact ? 'Live mastery' : 'AI domain mastery'}</h2>
          </div>
        </div>
        <p className="knowledge-empty">Mastery signals will appear as the interview collects evidence.</p>
      </section>
    )
  }

  return (
    <section className={`knowledge-map ${compact ? 'knowledge-map--compact' : ''}`}>
      <div className="knowledge-map__header">
        <div>
          <span className="section-kicker">Candidate knowledge map</span>
          <h2>{compact ? 'Live mastery' : 'AI domain mastery'}</h2>
        </div>
        {!compact && <span className="map-candidate">{map.candidate_id}</span>}
      </div>

      <div className="knowledge-list">
        {topics.map((topic) => {
          const score = Math.round(topic.score || 0)
          const confidence = Math.round((topic.confidence || 0) * 100)
          return (
            <article className="knowledge-topic" key={topic.topic}>
              <div className="knowledge-topic__top">
                <div>
                  <strong>{topic.topic}</strong>
                  {!compact && (
                    <span>{topic.questions_asked || 0} interview question{topic.questions_asked === 1 ? '' : 's'} · {confidenceLabel(topic.confidence)}</span>
                  )}
                </div>
                <b>{score}</b>
              </div>
              <div className="mastery-track" aria-label={`${topic.topic} mastery ${score} out of 100`}>
                <span style={{ width: `${score}%` }} />
              </div>
              {!compact && (
                <div className="knowledge-topic__meta">
                  <span>Confidence {confidence}%</span>
                  <span>Days {topic.related_days?.join(', ') || '—'}</span>
                </div>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}
