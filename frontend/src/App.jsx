import CandidateSelect from './pages/CandidateSelect'
import InterviewComplete from './pages/InterviewComplete'
import InterviewRoom from './pages/InterviewRoom'
import { useInterview } from './hooks/useInterview'

export default function App() {
  const interview = useInterview()

  if (interview.status === 'complete' && interview.candidate) {
    return (
      <InterviewComplete
        candidate={interview.candidate}
        feedback={interview.feedback}
        insights={interview.insights}
        questionCount={interview.questionCount}
        onReset={interview.resetInterview}
      />
    )
  }

  if (interview.candidate && interview.status !== 'idle') {
    return <InterviewRoom interview={interview} />
  }

  return (
    <CandidateSelect
      onStart={interview.startInterview}
      busy={interview.status === 'loading'}
      error={interview.error}
    />
  )
}
