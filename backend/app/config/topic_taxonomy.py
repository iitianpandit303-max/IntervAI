from app.models.knowledge_map import KnowledgeTopic


# Deliberately small, explicit taxonomy for the seven knowledge-map areas shown
# in the product. A curriculum day may contribute to more than one area because
# real AI systems overlap (for example, Day 24 connects agents, MCP and
# production integration).
TOPIC_DAYS: dict[KnowledgeTopic, tuple[int, ...]] = {
    KnowledgeTopic.RAG: (6, 7, 8, 9, 10, 11),
    KnowledgeTopic.VECTOR_DATABASES: (7, 8, 9, 10),
    KnowledgeTopic.PROMPT_ENGINEERING: (12, 13),
    KnowledgeTopic.AGENTIC_AI: (21, 22, 23, 24),
    KnowledgeTopic.MCP: (23, 24),
    KnowledgeTopic.DEPLOYMENT: (28, 30, 31),
    KnowledgeTopic.PRODUCTION_AI_SYSTEMS: (20, 24, 25, 26, 27, 28, 29, 30, 31),
}


def topics_for_day(day: int) -> list[KnowledgeTopic]:
    return [topic for topic, days in TOPIC_DAYS.items() if day in days]
