import { useMemo, useRef, useState } from 'react'
import { getInterviewInsights, interviewTurn } from '../api/interviewApi'
import { createSessionId, detectPressureQuestion } from '../utils/interviewUi'

export function useInterview() {
  const [candidate, setCandidate] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [questionCount, setQuestionCount] = useState(0)
  const [feedback, setFeedback] = useState(null)
  const [insights, setInsights] = useState(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [insightsError, setInsightsError] = useState('')
  const activeSessionRef = useRef(null)

  const currentAssistantMessage = useMemo(
    () => [...messages].reverse().find((message) => message.role === 'assistant'),
    [messages],
  )

  const pressureMode = Boolean(
    insights?.currentQuestion?.pressureChallengeType
      || (currentAssistantMessage && detectPressureQuestion(currentAssistantMessage.text)),
  )

  async function refreshInsights(targetSessionId) {
    if (!targetSessionId) return null

    try {
      const nextInsights = await getInterviewInsights(targetSessionId)

      // The user may have left the interview while the request was running.
      if (activeSessionRef.current !== targetSessionId) return null

      setInsights(nextInsights)
      setInsightsError('')
      return nextInsights
    } catch (requestError) {
      if (activeSessionRef.current !== targetSessionId) return null

      setInsightsError(requestError.message || 'Live mastery signals are temporarily unavailable.')
      return null
    }
  }

  async function startInterview(selectedCandidate) {
    if (!selectedCandidate || status === 'loading') return

    const nextSessionId = createSessionId()
    activeSessionRef.current = nextSessionId

    setStatus('loading')
    setError('')
    setInsightsError('')
    setCandidate(selectedCandidate)
    setSessionId(nextSessionId)
    setMessages([])
    setQuestionCount(0)
    setFeedback(null)
    setInsights(null)

    try {
      const response = await interviewTurn({
        sessionId: nextSessionId,
        candidate: selectedCandidate,
      })

      if (activeSessionRef.current !== nextSessionId) return

      setMessages([
        {
          id: `${nextSessionId}-assistant-1`,
          role: 'assistant',
          text: response.reply,
          pressure: detectPressureQuestion(response.reply),
        },
      ])
      setQuestionCount(response.done ? 0 : 1)
      setFeedback(response.feedback || null)
      await refreshInsights(nextSessionId)

      if (activeSessionRef.current !== nextSessionId) return
      setStatus(response.done ? 'complete' : 'active')
    } catch (requestError) {
      if (activeSessionRef.current !== nextSessionId) return

      activeSessionRef.current = null
      setCandidate(null)
      setSessionId(null)
      setMessages([])
      setQuestionCount(0)
      setFeedback(null)
      setInsights(null)
      setError(requestError.message || 'Unable to start the interview.')
      setStatus('idle')
    }
  }

  async function submitAnswer(answer) {
    const cleaned = answer.trim()
    if (!cleaned || !sessionId || status !== 'active') return false

    const targetSessionId = sessionId

    const candidateMessage = {
      id: `${targetSessionId}-candidate-${Date.now()}`,
      role: 'candidate',
      text: cleaned,
    }

    setMessages((current) => [...current, candidateMessage])
    setStatus('loading')
    setError('')

    try {
      const response = await interviewTurn({
        sessionId: targetSessionId,
        message: cleaned,
      })

      if (activeSessionRef.current !== targetSessionId) return false

      const assistantMessage = {
        id: `${targetSessionId}-assistant-${Date.now()}`,
        role: 'assistant',
        text: response.reply,
        pressure: detectPressureQuestion(response.reply),
      }

      setMessages((current) => [...current, assistantMessage])
      setFeedback(response.feedback || null)
      const latestInsights = await refreshInsights(targetSessionId)

      if (activeSessionRef.current !== targetSessionId) return false

      if (response.done) {
        setQuestionCount(latestInsights?.answeredQuestions || questionCount)
        setStatus('complete')
      } else {
        setQuestionCount((count) => count + 1)
        setStatus('active')
      }

      return true
    } catch (requestError) {
      if (activeSessionRef.current !== targetSessionId) return false

      setError(requestError.message || 'The interview request failed. Try again.')
      setStatus('active')
      return false
    }
  }

  function resetInterview() {
    // Invalidate any in-flight request before clearing UI state.
    activeSessionRef.current = null

    setCandidate(null)
    setSessionId(null)
    setMessages([])
    setQuestionCount(0)
    setFeedback(null)
    setInsights(null)
    setStatus('idle')
    setError('')
    setInsightsError('')
  }

  return {
    candidate,
    sessionId,
    messages,
    questionCount,
    feedback,
    insights,
    insightsError,
    status,
    error,
    pressureMode,
    startInterview,
    submitAnswer,
    resetInterview,
  }
}
