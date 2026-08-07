from app.models.api import FeedbackPayload, InterviewResponse
from app.models.answer_evaluation import RecommendedAction
from app.models.candidate import CandidateProfile
from app.models.session import InterviewSession, InterviewTurn
from app.repositories.curriculum_repository import CurriculumRepository
from app.repositories.session_repository import SessionRepository
from app.services.adaptive_question_generator import AdaptiveQuestionGenerator
from app.services.answer_evaluator import AnswerEvaluator
from app.services.interview_planner import InterviewPlanner
from app.services.pressure_question_generator import PressureQuestionGenerator
from app.services.question_generator import QuestionGenerator
from app.strategies.adaptive_policy import AdaptivePolicy
from app.strategies.coverage_policy import CoveragePolicy


class InterviewOrchestrator:
    """Stateful curriculum-aware interview workflow.

    Deterministic backend policy owns coverage and bounds. The LLM evaluates
    answers and words questions, while AdaptivePolicy decides whether enough
    reliable evidence exists to insert a same-day follow-up.
    """

    def __init__(
        self,
        sessions: SessionRepository | None = None,
        curriculum: CurriculumRepository | None = None,
        planner: InterviewPlanner | None = None,
        coverage: CoveragePolicy | None = None,
        question_generator: QuestionGenerator | None = None,
        answer_evaluator: AnswerEvaluator | None = None,
        adaptive_policy: AdaptivePolicy | None = None,
        adaptive_question_generator: AdaptiveQuestionGenerator | None = None,
        pressure_question_generator: PressureQuestionGenerator | None = None,
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
        self.answer_evaluator = answer_evaluator or AnswerEvaluator(
            curriculum=self.curriculum
        )
        self.adaptive_policy = adaptive_policy or AdaptivePolicy()
        self.adaptive_question_generator = (
            adaptive_question_generator
            or AdaptiveQuestionGenerator(curriculum=self.curriculum)
        )
        self.pressure_question_generator = (
            pressure_question_generator
            or PressureQuestionGenerator(curriculum=self.curriculum)
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
        cleaned_answer = message.strip()
        evaluation = self.answer_evaluator.evaluate(
            candidate=session.candidate,
            question=current,
            answer=cleaned_answer,
        )
        session.turns.append(
            InterviewTurn(
                question_id=current.question_id,
                question=current.text,
                answer=cleaned_answer,
                evaluation=evaluation,
            )
        )
        session.current_index += 1

        decision = self.adaptive_policy.decide(
            session=session,
            current=current,
            evaluation=evaluation,
        )
        if decision.should_insert_followup:
            if decision.action is RecommendedAction.PRESSURE:
                followup = self.pressure_question_generator.generate(
                    candidate=session.candidate,
                    previous=current,
                    answer=cleaned_answer,
                    evaluation=evaluation,
                    question_id=(
                        f"{current.question_id}-p{session.pressure_followups_used + 1}"
                    ),
                )
                session.pressure_followups_used += 1
            else:
                followup = self.adaptive_question_generator.generate(
                    candidate=session.candidate,
                    previous=current,
                    answer=cleaned_answer,
                    evaluation=evaluation,
                    action=decision.action,
                    question_id=(
                        f"{current.question_id}-a{session.adaptive_followups_used + 1}"
                    ),
                )

            session.questions.insert(session.current_index, followup)
            session.adaptive_followups_used += 1
            self.sessions.save(session)
            return InterviewResponse(reply=followup.text, done=False)

        plan_exhausted = session.current_index >= len(session.questions)
        if plan_exhausted:
            if not self.coverage.can_finish(session):
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
                f"covering {status.unique_answered_days} curriculum days. "
                f"{session.adaptive_followups_used} adaptive follow-up(s) were used, "
                f"including {session.pressure_followups_used} pressure challenge(s)."
            ),
            strengths=["Completed a curriculum-grounded adaptive technical interview."],
            gaps=["Knowledge-map aggregation and final readiness scoring are not added yet."],
            next=["Use stored evaluations to update topic mastery and generate the readiness report."],
        )
        return InterviewResponse(reply="Interview completed.", done=True, feedback=feedback)
