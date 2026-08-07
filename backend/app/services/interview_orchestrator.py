from app.models.api import InterviewResponse
from app.models.answer_evaluation import RecommendedAction
from app.models.candidate import CandidateProfile
from app.models.session import InterviewSession, InterviewTurn
from app.models.interview_insights import CurrentQuestionInsight, InterviewInsightsResponse
from app.repositories.curriculum_repository import CurriculumRepository
from app.repositories.session_repository import SessionRepository
from app.services.adaptive_question_generator import AdaptiveQuestionGenerator
from app.services.answer_evaluator import AnswerEvaluator
from app.services.feedback_service import FeedbackService
from app.services.interview_planner import InterviewPlanner
from app.services.knowledge_map import KnowledgeMapService
from app.services.memory_manager import MemoryManager
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
        knowledge_map_service: KnowledgeMapService | None = None,
        memory_manager: MemoryManager | None = None,
        feedback_service: FeedbackService | None = None,
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
        self.knowledge_map_service = knowledge_map_service or KnowledgeMapService()
        self.memory_manager = memory_manager or MemoryManager()
        self.feedback_service = feedback_service or FeedbackService(
            curriculum=self.curriculum,
            coverage=self.coverage,
        )

    def start(self, session_id: str, candidate: CandidateProfile) -> InterviewResponse:
        if self.sessions.exists(session_id):
            raise ValueError("session_exists")

        questions = self.planner.build_plan(candidate)
        knowledge_map = self.knowledge_map_service.initialize(candidate)
        memory = self.memory_manager.initialize()
        questions[0] = self.question_generator.materialize(
            candidate=candidate,
            planned=questions[0],
            working_memory=self.memory_manager.render_context(memory, knowledge_map),
        )
        session = InterviewSession(
            session_id=session_id,
            candidate=candidate,
            questions=questions,
            knowledge_map=knowledge_map,
            memory=memory,
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
        if session.knowledge_map is None:
            # Backward-compatible recovery for sessions created before Commit 10.
            session.knowledge_map = self.knowledge_map_service.initialize(session.candidate)
        if session.memory is None:
            # Backward-compatible recovery for sessions created before Commit 11.
            session.memory = self.memory_manager.initialize()

        prior_memory_context = self.memory_manager.render_context(
            session.memory, session.knowledge_map
        )
        evaluation = self.answer_evaluator.evaluate(
            candidate=session.candidate,
            question=current,
            answer=cleaned_answer,
            working_memory=prior_memory_context,
        )
        turn = InterviewTurn(
            question_id=current.question_id,
            question=current.text,
            answer=cleaned_answer,
            evaluation=evaluation,
        )
        session.turns.append(turn)
        session.knowledge_map = self.knowledge_map_service.update(
            session.knowledge_map,
            question=current,
            evaluation=evaluation,
        )
        session.memory = self.memory_manager.update(
            session.memory,
            question=current,
            turn=turn,
            knowledge_map=session.knowledge_map,
            answered_turn_count=len(session.turns),
        )
        working_memory = self.memory_manager.render_context(
            session.memory, session.knowledge_map
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
                    working_memory=working_memory,
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
                    working_memory=working_memory,
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
            working_memory=working_memory,
        )
        session.questions[session.current_index] = next_question
        self.sessions.save(session)
        return InterviewResponse(reply=next_question.text, done=False)


    def get_insights(self, session_id: str) -> InterviewInsightsResponse:
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError("session_not_found")

        if session.done and session.final_report is None:
            session.final_report = self.feedback_service.build_report(session)
            self.sessions.save(session)

        question_by_id = {question.question_id: question for question in session.questions}
        days_covered = sorted({
            question_by_id[turn.question_id].day
            for turn in session.turns
            if turn.question_id in question_by_id
        })

        current = None
        if not session.done and session.current_index < len(session.questions):
            question = session.questions[session.current_index]
            current = CurrentQuestionInsight(
                questionId=question.question_id,
                day=question.day,
                title=question.title,
                questionType=question.question_type.value,
                difficulty=question.difficulty.value,
                adaptiveAction=(
                    question.adaptive_action.value if question.adaptive_action else None
                ),
                pressureChallengeType=(
                    question.pressure_challenge_type.value
                    if question.pressure_challenge_type
                    else None
                ),
            )

        return InterviewInsightsResponse(
            sessionId=session.session_id,
            done=session.done,
            answeredQuestions=len(session.turns),
            plannedQuestions=len(session.questions),
            curriculumDaysCovered=days_covered,
            adaptiveFollowupsUsed=session.adaptive_followups_used,
            pressureChallengesUsed=session.pressure_followups_used,
            currentQuestion=current,
            knowledgeMap=session.knowledge_map,
            finalReport=session.final_report,
        )

    def _completed_response(self, session: InterviewSession) -> InterviewResponse:
        if session.final_report is None:
            session.final_report = self.feedback_service.build_report(session)
            self.sessions.save(session)
        feedback = self.feedback_service.to_api_feedback(session.final_report)
        return InterviewResponse(reply="Interview completed.", done=True, feedback=feedback)
