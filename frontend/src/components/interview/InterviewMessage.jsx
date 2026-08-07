export default function InterviewMessage({ message, candidateName }) {
  const assistant = message.role === 'assistant'

  return (
    <article className={`message message--${message.role} ${message.pressure ? 'message--pressure' : ''}`}>
      <div className="message__meta">
        <span>{assistant ? 'IntervAI' : candidateName}</span>
        {message.pressure && <span className="pressure-chip">Pressure mode</span>}
      </div>
      <p>{message.text}</p>
    </article>
  )
}
