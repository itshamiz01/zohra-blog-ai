"""
Zohra — Research Planner & Question Decomposer.

Decomposes content opportunities into goal-driven research questions with priorities,
evidence rigor requirements (primary source vs corroboration), and targeted search queries.
"""

from __future__ import annotations

from typing import Any

from app.schemas.opportunity import ContentOpportunityPackage
from app.schemas.research import QueryType, QuestionPriority, QuestionType


class PlannedQuestion:
    def __init__(
        self,
        question: str,
        question_type: QuestionType,
        priority: QuestionPriority,
        requires_primary_source: bool = False,
        requires_multiple_sources: bool = False,
        queries: list[dict[str, Any]] | None = None,
    ):
        self.question = question
        self.question_type = question_type
        self.priority = priority
        self.requires_primary_source = requires_primary_source
        self.requires_multiple_sources = requires_multiple_sources
        self.queries = queries or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "question_type": self.question_type.value,
            "priority": self.priority.value,
            "requires_primary_source": self.requires_primary_source,
            "requires_multiple_sources": self.requires_multiple_sources,
            "queries": self.queries,
        }


class ResearchPlanner:
    """Decomposes topic opportunities into actionable, prioritized research questions & queries."""

    def plan_research(
        self,
        package: ContentOpportunityPackage,
        research_depth: str = "STANDARD",
    ) -> list[PlannedQuestion]:
        topic = package.topic.strip()
        entities = package.entities or []
        primary_entity = entities[0] if entities else topic
        content_type = package.content_type.lower()
        lang = package.language or "en"
        country = package.country or "US"

        questions: list[PlannedQuestion] = []

        # 1. Foundational questions (all content types)
        questions.append(
            PlannedQuestion(
                question=f"What is {primary_entity} and what is its core purpose?",
                question_type=QuestionType.DEFINITION,
                priority=QuestionPriority.HIGH,
                requires_primary_source=True,
                requires_multiple_sources=False,
                queries=[
                    {
                        "query": f"{primary_entity} official overview what is",
                        "query_type": QueryType.PRIMARY_SOURCE.value,
                        "priority": "HIGH",
                    },
                    {
                        "query": f"{primary_entity} documentation about",
                        "query_type": QueryType.OFFICIAL_DOCUMENTATION.value,
                        "priority": "HIGH",
                    },
                ],
            )
        )

        questions.append(
            PlannedQuestion(
                question=f"Who developed or released {primary_entity} and when was it launched?",
                question_type=QuestionType.TIMELINE,
                priority=QuestionPriority.HIGH,
                requires_primary_source=True,
                requires_multiple_sources=False,
                queries=[
                    {
                        "query": f"{primary_entity} release date official announcement",
                        "query_type": QueryType.PRIMARY_SOURCE.value,
                        "priority": "HIGH",
                    }
                ],
            )
        )

        # 2. Content-type specific decompositions
        if content_type in ("tutorial", "guide", "explainer"):
            questions.append(
                PlannedQuestion(
                    question=f"What are the step-by-step workflow and key features of {primary_entity}?",
                    question_type=QuestionType.PROCESS,
                    priority=QuestionPriority.CRITICAL,
                    requires_primary_source=True,
                    requires_multiple_sources=True,
                    queries=[
                        {
                            "query": f"{primary_entity} how to use tutorial step by step",
                            "query_type": QueryType.OFFICIAL_DOCUMENTATION.value,
                            "priority": "CRITICAL",
                        },
                        {
                            "query": f"{primary_entity} quickstart guide documentation",
                            "query_type": QueryType.OFFICIAL_DOCUMENTATION.value,
                            "priority": "HIGH",
                        },
                    ],
                )
            )
            questions.append(
                PlannedQuestion(
                    question=f"What are the technical requirements, prerequisites, and system specifications for {primary_entity}?",
                    question_type=QuestionType.TECHNICAL,
                    priority=QuestionPriority.HIGH,
                    requires_primary_source=True,
                    requires_multiple_sources=False,
                    queries=[
                        {
                            "query": f"{primary_entity} system requirements prerequisites api limits",
                            "query_type": QueryType.OFFICIAL_DOCUMENTATION.value,
                            "priority": "HIGH",
                        }
                    ],
                )
            )
            questions.append(
                PlannedQuestion(
                    question=f"What are the known limitations, constraints, and bugs reported for {primary_entity}?",
                    question_type=QuestionType.LIMITATION,
                    priority=QuestionPriority.HIGH,
                    requires_primary_source=False,
                    requires_multiple_sources=True,
                    queries=[
                        {
                            "query": f"{primary_entity} limitations known issues problems site:reddit.com OR site:github.com",
                            "query_type": QueryType.COMMUNITY.value,
                            "priority": "HIGH",
                        },
                        {
                            "query": f"{primary_entity} technical constraints limits",
                            "query_type": QueryType.OFFICIAL_DOCUMENTATION.value,
                            "priority": "MEDIUM",
                        },
                    ],
                )
            )

        elif content_type in ("pricing", "review", "commercial_investigation"):
            questions.append(
                PlannedQuestion(
                    question=f"What is the official pricing, tier breakdown, and free plan availability for {primary_entity}?",
                    question_type=QuestionType.PRICING,
                    priority=QuestionPriority.CRITICAL,
                    requires_primary_source=True,
                    requires_multiple_sources=False,
                    queries=[
                        {
                            "query": f"{primary_entity} pricing tiers plans official cost",
                            "query_type": QueryType.PRIMARY_SOURCE.value,
                            "priority": "CRITICAL",
                        },
                        {
                            "query": f"{primary_entity} free tier subscription cost {country}",
                            "query_type": QueryType.PRIMARY_SOURCE.value,
                            "priority": "HIGH",
                        },
                    ],
                )
            )
            questions.append(
                PlannedQuestion(
                    question=f"Are there commercial usage rights, regional restrictions, or refund policies for {primary_entity}?",
                    question_type=QuestionType.LEGAL,
                    priority=QuestionPriority.HIGH,
                    requires_primary_source=True,
                    requires_multiple_sources=False,
                    queries=[
                        {
                            "query": f"{primary_entity} terms of service commercial rights licensing",
                            "query_type": QueryType.OFFICIAL_DOCUMENTATION.value,
                            "priority": "HIGH",
                        }
                    ],
                )
            )

        elif content_type in ("comparison", "alternatives"):
            other_entities = entities[1:] if len(entities) > 1 else ["alternatives"]
            competitor_str = " vs ".join(other_entities)
            questions.append(
                PlannedQuestion(
                    question=f"How does {primary_entity} compare to {competitor_str} in features, pricing, and benchmarks?",
                    question_type=QuestionType.COMPARISON,
                    priority=QuestionPriority.CRITICAL,
                    requires_primary_source=False,
                    requires_multiple_sources=True,
                    queries=[
                        {
                            "query": f"{primary_entity} vs {competitor_str} comparison benchmark differences",
                            "query_type": QueryType.GENERAL_WEB.value,
                            "priority": "CRITICAL",
                        },
                        {
                            "query": f"{primary_entity} vs {competitor_str} pricing feature matrix",
                            "query_type": QueryType.GENERAL_WEB.value,
                            "priority": "HIGH",
                        },
                    ],
                )
            )
            questions.append(
                PlannedQuestion(
                    question=f"What are the top pros and cons of {primary_entity} compared to alternative tools?",
                    question_type=QuestionType.USER_EXPERIENCE,
                    priority=QuestionPriority.HIGH,
                    requires_primary_source=False,
                    requires_multiple_sources=True,
                    queries=[
                        {
                            "query": f"{primary_entity} pros and cons real user review",
                            "query_type": QueryType.COMMUNITY.value,
                            "priority": "HIGH",
                        }
                    ],
                )
            )

        else:  # breaking_news, news_analysis
            questions.append(
                PlannedQuestion(
                    question=f"What specific announcement or change occurred regarding {topic}?",
                    question_type=QuestionType.PRODUCT,
                    priority=QuestionPriority.CRITICAL,
                    requires_primary_source=True,
                    requires_multiple_sources=True,
                    queries=[
                        {
                            "query": f"{topic} official announcement press release",
                            "query_type": QueryType.PRIMARY_SOURCE.value,
                            "priority": "CRITICAL",
                        },
                        {
                            "query": f"{topic} news updates details",
                            "query_type": QueryType.NEWS.value,
                            "priority": "HIGH",
                        },
                    ],
                )
            )

        # 3. Always check pricing/availability if not already included
        if not any(q.question_type == QuestionType.PRICING for q in questions):
            questions.append(
                PlannedQuestion(
                    question=f"What does {primary_entity} cost and is there a free version?",
                    question_type=QuestionType.PRICING,
                    priority=QuestionPriority.HIGH,
                    requires_primary_source=True,
                    requires_multiple_sources=False,
                    queries=[
                        {
                            "query": f"{primary_entity} pricing cost free trial",
                            "query_type": QueryType.PRIMARY_SOURCE.value,
                            "priority": "HIGH",
                        }
                    ],
                )
            )

        # 4. Integrate questions discovered from Part 3 package
        for q_text in (package.questions or [])[:4]:
            clean_q = q_text.strip()
            if clean_q and not any(clean_q.lower() in q.question.lower() for q in questions):
                # Infer type
                q_type = QuestionType.PRODUCT
                q_lower = clean_q.lower()
                if any(w in q_lower for w in ("cost", "price", "pricing", "free")):
                    q_type = QuestionType.PRICING
                elif any(w in q_lower for w in ("how to", "steps", "workflow", "use")):
                    q_type = QuestionType.PROCESS
                elif any(w in q_lower for w in ("vs", "compare", "difference", "alternative")):
                    q_type = QuestionType.COMPARISON
                elif any(w in q_lower for w in ("error", "bug", "problem", "not working", "limit")):
                    q_type = QuestionType.LIMITATION

                questions.append(
                    PlannedQuestion(
                        question=clean_q,
                        question_type=q_type,
                        priority=QuestionPriority.MEDIUM,
                        requires_primary_source=False,
                        requires_multiple_sources=True,
                        queries=[
                            {
                                "query": clean_q,
                                "query_type": QueryType.GENERAL_WEB.value,
                                "priority": "MEDIUM",
                            }
                        ],
                    )
                )

        # 5. Expand if DEEP or CRITICAL research depth
        if research_depth in ("DEEP", "CRITICAL"):
            questions.append(
                PlannedQuestion(
                    question=f"What are the regional availability and localization differences for {primary_entity} (e.g. {country})?",
                    question_type=QuestionType.AVAILABILITY,
                    priority=QuestionPriority.HIGH,
                    requires_primary_source=True,
                    requires_multiple_sources=False,
                    queries=[
                        {
                            "query": f"{primary_entity} available countries regional rollout {country}",
                            "query_type": QueryType.OFFICIAL_DOCUMENTATION.value,
                            "priority": "HIGH",
                        }
                    ],
                )
            )
            questions.append(
                PlannedQuestion(
                    question=f"What security, privacy, and compliance certifications apply to {primary_entity}?",
                    question_type=QuestionType.LEGAL,
                    priority=QuestionPriority.MEDIUM,
                    requires_primary_source=True,
                    requires_multiple_sources=False,
                    queries=[
                        {
                            "query": f"{primary_entity} privacy policy gdpr security compliance",
                            "query_type": QueryType.OFFICIAL_DOCUMENTATION.value,
                            "priority": "MEDIUM",
                        }
                    ],
                )
            )

        # Apply localized language/country parameters to queries
        for q in questions:
            for qy in q.queries:
                qy.setdefault("language", lang)
                qy.setdefault("country", country)

        return questions
