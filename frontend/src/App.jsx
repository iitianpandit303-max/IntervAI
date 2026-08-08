import { useEffect, useRef } from 'react'
import CandidateSelect from './pages/CandidateSelect'
import InterviewComplete from './pages/InterviewComplete'
import InterviewRoom from './pages/InterviewRoom'
import { useInterview } from './hooks/useInterview'

export default function App() {
  const interview = useInterview()
  const interviewHistoryActive = useRef(false)

  // Add one browser-history entry once an interview successfully starts.
  // This makes the browser Back button return to candidate selection
  // instead of leaving the IntervAI site immediately.
  useEffect(() => {
    const interviewStarted = Boolean(
      interview.candidate
        && (interview.status === 'active' || interview.status === 'complete'),
    )

    if (interviewStarted && !interviewHistoryActive.current) {
      window.history.pushState(
        { ...window.history.state, intervaiView: 'interview' },
        '',
        window.location.href,
      )
      interviewHistoryActive.current = true
    }

    if (!interview.candidate || interview.status === 'idle') {
      interviewHistoryActive.current = false
    }
  }, [interview.candidate, interview.status])

  // If the user presses the browser Back button during an interview,
  // reset the local interview state and reveal candidate selection.
  useEffect(() => {
    function handlePopState() {
      if (
        interviewHistoryActive.current
        && interview.candidate
        && interview.status !== 'idle'
      ) {
        interviewHistoryActive.current = false
        interview.resetInterview()
      }
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [interview.candidate, interview.status, interview.resetInterview])

  function returnToCandidates() {
    const ownsInterviewHistoryEntry = Boolean(
      interviewHistoryActive.current
        && window.history.state?.intervaiView === 'interview',
    )

    interviewHistoryActive.current = false
    interview.resetInterview()

    // Remove the synthetic interview history entry so repeated navigation
    // does not leave duplicate copies of the same URL in browser history.
    if (ownsInterviewHistoryEntry) {
      window.history.back()
    }
  }

  if (interview.status === 'complete' && interview.candidate) {
    return (
      <InterviewComplete
        candidate={interview.candidate}
        feedback={interview.feedback}
        insights={interview.insights}
        questionCount={interview.questionCount}
        onReset={returnToCandidates}
      />
    )
  }

  if (interview.candidate && interview.status !== 'idle') {
    return (
      <InterviewRoom
        interview={interview}
        onExit={returnToCandidates}
      />
    )
  }

  return (
    <CandidateSelect
      onStart={interview.startInterview}
      busy={interview.status === 'loading'}
      error={interview.error}
    />
  )
}
