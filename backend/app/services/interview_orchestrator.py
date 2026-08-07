from app.models.api import FeedbackPayload, InterviewResponse
from app.models.candidate import CandidateProfile
from app.models.session import InterviewSession, InterviewTurn
from app.repositories.curriculum_repository import CurriculumRepository
from app.repositories.session_repository import SessionRepository
from app.services.interview_planner import InterviewPlanner
from app.services.question_generator import QuestionGenerator
from app.strategies.coverage_policy import CoveragePolicy


class InterviewOrchestrator:
    """Curriculum-aware workflow with guarded, just-in-time LLM question wording.

    Backend policy still owns coverage, day selection, question type and difficulty.
    The LLM only turns a validated plan slot into natural interviewer language.
    """

    def __init__(
        self,
        sessions: SessionRepository | None = None,
        curriculum: CurriculumRepository | None = None,
        planner: InterviewPlanner | None = None,
        coverage: CoveragePolicy | None = None,
        question_generator: QuestionGenerator | None = None,
    ) -> None:
        self.sessions = sessions or SessionRepository()
        self.curriculum = curriculum or CurriculumRepository()
        self.coverage = coverage or CoveragePolicy()
        self.planner = planner or InterviewPlanner(
            curriculum=self.curriculum,
            coverage=self.coverage,
        )
        self.question_generator = question_generator or QuestionGenerator(
            curriculum=self.curriculum
        )

    def start(self, session_id: str, candidate: CandidateProfile) -> InterviewResponse:
        if self.sessions.exists(session_id):
            raise ValueError("session_exists")

        questions = self.planner.build_plan(candidate)
        questions[0] = self.question_generator.materialize(
            candidate=candidate,
            planned=questions[0],
        )
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

        plan_exhausted = session.current_index >= len(session.questions)
        if plan_exhausted:
            if not self.coverage.can_finish(session):
                # This should be impossible because InterviewPlanner validates the
                # plan before a session starts. Keeping the guard here prevents a
                # future adaptive planner from accidentally violating the contract.
                raise RuntimeError("interview_coverage_requirements_not_met")
            session.done = True
            self.sessions.save(session)
            return self._completed_response(session)

        next_question = self.question_generator.materialize(
            candidate=session.candidate,
            planned=session.questions[session.current_index],
        )
        session.questions[session.current_index] = next_question
        self.sessions.save(session)
        return InterviewResponse(reply=next_question.text, done=False)

    def _completed_response(self, session: InterviewSession) -> InterviewResponse:
        status = self.coverage.status(session)
        feedback = FeedbackPayload(
            summary=(
                f"Interview completed after {status.answered_questions} answered questions "
                f"covering {status.unique_answered_days} curriculum days. Answer scoring and "
                "adaptive follow-ups are intentionally deferred to the next feature commits."
            ),
            strengths=["Completed the curriculum-aware interview flow."],
            gaps=["Detailed answer scoring is not enabled in this milestone."],
            next=["Enable structured LLM evaluation and adaptive follow-up logic."],
        )
        return InterviewResponse(reply="Interview completed.", done=True, feedback=feedback)
