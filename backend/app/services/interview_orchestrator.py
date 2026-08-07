from app.models.api import FeedbackPayload, InterviewResponse
from app.models.candidate import CandidateProfile
from app.models.session import InterviewSession, InterviewTurn, PlannedQuestion
from app.repositories.curriculum_repository import CurriculumRepository
from app.repositories.session_repository import SessionRepository


MIN_QUESTIONS = 8


class InterviewOrchestrator:
    """Commit-3 deterministic interview engine.

    This intentionally contains no LLM. It proves the API/session contract first.
    Later commits will replace question selection and evaluation while preserving
    this public contract.
    """

    def __init__(
        self,
        sessions: SessionRepository | None = None,
        curriculum: CurriculumRepository | None = None,
    ) -> None:
        self.sessions = sessions or SessionRepository()
        self.curriculum = curriculum or CurriculumRepository()

    def start(self, session_id: str, candidate: CandidateProfile) -> InterviewResponse:
        if self.sessions.exists(session_id):
            raise ValueError("session_exists")

        questions = self._build_mock_plan(candidate)
        session = InterviewSession(
            session_id=session_id,
            candidate=candidate,
            questions=questions,
        )
        self.sessions.save(session)

        first = questions[0]
        return InterviewResponse(
            reply=(
                f"Welcome, {candidate.member.name}. Let's begin your technical interview. "
                f"{first.text}"
            ),
            done=False,
        )

    def continue_interview(self, session_id: str, message: str) -> InterviewResponse:
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError("session_not_found")
        if session.done:
            return self._completed_response(session)

        current = session.questions[session.current_index]
        session.turns.append(
            InterviewTurn(
                question_id=current.question_id,
                question=current.text,
                answer=message.strip(),
            )
        )
        session.current_index += 1

        if session.current_index >= len(session.questions):
            session.done = True
            self.sessions.save(session)
            return self._completed_response(session)

        next_question = session.questions[session.current_index]
        self.sessions.save(session)
        return InterviewResponse(reply=next_question.text, done=False)

    def _build_mock_plan(self, candidate: CandidateProfile) -> list[PlannedQuestion]:
        unique_days: list[int] = []
        for mission in candidate.missions:
            if mission.day not in unique_days and self.curriculum.get_day(mission.day):
                unique_days.append(mission.day)

        # Supplied candidate profiles contain enough mission days. Fall back to the
        # curriculum only so the API remains testable with a smaller valid profile.
        if len(unique_days) < MIN_QUESTIONS:
            for day in self.curriculum.all_days():
                if day.day not in unique_days:
                    unique_days.append(day.day)
                if len(unique_days) >= MIN_QUESTIONS:
                    break

        selected_days = unique_days[:MIN_QUESTIONS]
        questions: list[PlannedQuestion] = []
        for index, day_number in enumerate(selected_days, start=1):
            day = self.curriculum.get_day(day_number)
            objective = day.objectives[min(index - 1, len(day.objectives) - 1)]
            text = (
                f"Question {index}: From Day {day.day} — {day.title}: "
                f"How would you explain or apply this objective in practice: {objective}?"
            )
            questions.append(
                PlannedQuestion(
                    question_id=f"q{index}",
                    day=day.day,
                    title=day.title,
                    text=text,
                )
            )
        return questions

    def _completed_response(self, session: InterviewSession) -> InterviewResponse:
        covered_days = sorted({question.day for question in session.questions})
        feedback = FeedbackPayload(
            summary=(
                f"Interview completed after {len(session.turns)} answered questions "
                f"covering {len(covered_days)} curriculum days. Adaptive scoring is "
                "scheduled for the next feature commits."
            ),
            strengths=["Completed the full mocked interview flow."],
            gaps=["Detailed answer scoring is not enabled in this foundation milestone."],
            next=["Enable curriculum-grounded LLM evaluation and adaptive follow-up logic."],
        )
        return InterviewResponse(reply="Interview completed.", done=True, feedback=feedback)
