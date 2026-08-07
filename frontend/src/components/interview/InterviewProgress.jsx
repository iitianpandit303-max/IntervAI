export default function InterviewProgress({ questionCount, pressureMode }) {
  const minimumQuestions = 8
  const progress = Math.min(100, Math.round((questionCount / minimumQuestions) * 100))

  return (
    <div className="interview-progress">
      <div className="interview-progress__copy">
        <span>Question {questionCount}</span>
        <span>{questionCount < minimumQuestions ? `${minimumQuestions - questionCount} minimum remaining` : 'Minimum coverage reached'}</span>
      </div>
      <div className="progress-track" aria-label={`Interview minimum progress ${progress}%`}>
        <span style={{ width: `${progress}%` }} />
      </div>
      <div className={`interview-mode ${pressureMode ? 'interview-mode--pressure' : ''}`}>
        <span className="mode-dot" />
        {pressureMode ? 'Pressure challenge detected' : 'Adaptive interview active'}
      </div>
    </div>
  )
}
