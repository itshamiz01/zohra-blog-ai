"""
Zohra — Search Intent Classification & Strength Engine.

Classifies queries into primary and secondary search intents across 10 canonical types,
calculates intent confidence and intent specificity strength, and provides SERP-based
validation adjustment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.constants import SearchIntent


@dataclass
class IntentClassificationResult:
    query: str
    primary_intent: SearchIntent
    secondary_intent: SearchIntent | None
    confidence: float
    intent_strength_score: float  # 0 to 100 specificity score
    evidence: list[str]


class SearchIntentClassifier:
    """Classifies search queries into granular intents with confidence & strength metrics."""

    # Intent signature patterns (ordered by discriminative specificity)
    TUTORIAL_PATTERNS = [
        r"\bhow\s+to\b",
        r"\btutorial\b",
        r"\bstep\s+by\s+step\b",
        r"\bguide\b",
        r"\bfor\s+beginners?\b",
        r"\bgetting\s+started\b",
        r"\bwalkthrough\b",
        r"\bhow\s+do\s+(?:i|we|you)\b",
        r"\blearn\b",
        r"\bcode\s+example\b",
        r"\bsetup\s+guide\b",
    ]

    COMPARISON_PATTERNS = [
        r"\bvs\b",
        r"\bversus\b",
        r"\bcompared\s+to\b",
        r"\bdifference\s+between\b",
        r"\balternatives?\b",
        r"\bor\b",
        r"\bwhich\s+is\s+better\b",
        r"\bpros\s+and\s+cons\b",
    ]

    TROUBLESHOOTING_PATTERNS = [
        r"\bnot\s+working\b",
        r"\berror\b",
        r"\bfix\b",
        r"\bissue\b",
        r"\bproblem\b",
        r"\bfailing\b",
        r"\bfailed\b",
        r"\bcrash(?:ed|ing)?\b",
        r"\btroubleshoot(?:ing)?\b",
        r"\bwhy\s+is\b.*\b(down|failing|broken)\b",
        r"\bhow\s+to\s+fix\b",
    ]

    TRANSACTIONAL_PATTERNS = [
        r"\bbuy\b",
        r"\bpurchase\b",
        r"\bdiscount\b",
        r"\bcoupon\b",
        r"\bcheap\b",
        r"\border\b",
        r"\bdeal\b",
        r"\bdownload\b",
        r"\bcheckout\b",
        r"\bpromo\s+code\b",
    ]

    COMMERCIAL_PATTERNS = [
        r"\bpricing\b",
        r"\bprice\b",
        r"\bcost\b",
        r"\bplans?\b",
        r"\breview\b",
        r"\brating\b",
        r"\bbest\b",
        r"\btop\b",
        r"\bworth\s+it\b",
        r"\bfree\s+(?:vs|or)\s+paid\b",
        r"\bfeatures\b",
        r"\benterprise\b",
    ]

    NEWS_PATTERNS = [
        r"\blaunch(?:ed|es)?\b",
        r"\brelease\s+date\b",
        r"\bannounced?\b",
        r"\bbreaking\b",
        r"\bupdate\b",
        r"\bnew\b",
        r"\btoday\b",
        r"\byesterday\b",
        r"\b202[6-9]\b",
        r"\bunveils?\b",
    ]

    REFERENCE_PATTERNS = [
        r"\bapi\b",
        r"\bdocumentation\b",
        r"\bdocs\b",
        r"\bspecs?\b",
        r"\bspecifications?\b",
        r"\bcheat\s*sheet\b",
        r"\bsyntax\b",
        r"\brequirements?\b",
        r"\blimits?\b",
        r"\bsupported\s+models?\b",
    ]

    LOCAL_PATTERNS = [
        r"\bnear\s+me\b",
        r"\bin\s+[a-z]+(?:\s+[a-z]+)?$",
        r"\baddress\b",
        r"\blocation\b",
        r"\bphone\s+number\b",
    ]

    NAVIGATIONAL_PATTERNS = [
        r"\blogin\b",
        r"\bsign\s+in\b",
        r"\bportal\b",
        r"\bofficial\s+site\b",
        r"\bwebsite\b",
        r"\bapp\s+store\b",
        r"\baccount\b",
        r"\bdashboard\b",
    ]

    INFORMATIONAL_PATTERNS = [
        r"\bwhat\s+is\b",
        r"\bwhat\s+are\b",
        r"\bmeaning\b",
        r"\bdefinition\b",
        r"\bexplained\b",
        r"\bwhy\s+does\b",
        r"\bhistory\s+of\b",
        r"\bhow\s+does\b.*\bwork\b",
    ]

    def __init__(self) -> None:
        # Precompile regexes
        self._compiled_patterns = {
            SearchIntent.TUTORIAL: [re.compile(p, re.IGNORECASE) for p in self.TUTORIAL_PATTERNS],
            SearchIntent.COMPARISON: [re.compile(p, re.IGNORECASE) for p in self.COMPARISON_PATTERNS],
            SearchIntent.TROUBLESHOOTING: [re.compile(p, re.IGNORECASE) for p in self.TROUBLESHOOTING_PATTERNS],
            SearchIntent.TRANSACTIONAL: [re.compile(p, re.IGNORECASE) for p in self.TRANSACTIONAL_PATTERNS],
            SearchIntent.COMMERCIAL_INVESTIGATION: [re.compile(p, re.IGNORECASE) for p in self.COMMERCIAL_PATTERNS],
            SearchIntent.NEWS: [re.compile(p, re.IGNORECASE) for p in self.NEWS_PATTERNS],
            SearchIntent.REFERENCE: [re.compile(p, re.IGNORECASE) for p in self.REFERENCE_PATTERNS],
            SearchIntent.LOCAL: [re.compile(p, re.IGNORECASE) for p in self.LOCAL_PATTERNS],
            SearchIntent.NAVIGATIONAL: [re.compile(p, re.IGNORECASE) for p in self.NAVIGATIONAL_PATTERNS],
            SearchIntent.INFORMATIONAL: [re.compile(p, re.IGNORECASE) for p in self.INFORMATIONAL_PATTERNS],
        }

    def classify(self, query: str) -> IntentClassificationResult:
        """Classifies a search query into primary & secondary intents with strength score."""
        clean_query = query.strip()
        matches: list[tuple[SearchIntent, int, str]] = []

        for intent, patterns in self._compiled_patterns.items():
            for p in patterns:
                m = p.search(clean_query)
                if m:
                    # Give higher precedence to explicit comparative, tutorial, troubleshooting patterns
                    weight = 2 if intent in (SearchIntent.TUTORIAL, SearchIntent.COMPARISON, SearchIntent.TROUBLESHOOTING) else 1
                    matches.append((intent, weight, m.group(0)))

        # Default fallback is INFORMATIONAL
        if not matches:
            primary = SearchIntent.INFORMATIONAL
            secondary = None
            confidence = 0.65
            evidence = ["fallback_default_informational"]
        else:
            # Score matches
            intent_scores: dict[SearchIntent, int] = {}
            for intent, weight, _ in matches:
                intent_scores[intent] = intent_scores.get(intent, 0) + weight

            sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
            primary = sorted_intents[0][0]
            secondary = sorted_intents[1][0] if len(sorted_intents) > 1 and sorted_intents[1][0] != primary else None

            # For comparison queries with no explicit secondary intent, default secondary to commercial investigation
            if primary == SearchIntent.COMPARISON and secondary is None:
                secondary = SearchIntent.COMMERCIAL_INVESTIGATION

            # Calculate confidence based on pattern match clarity
            confidence = min(0.98, 0.70 + (0.10 * intent_scores[primary]))
            evidence = [f"{m[0].value}: '{m[2]}'" for m in matches[:4]]

        # Compute intent strength score (0 to 100)
        strength = self.calculate_intent_strength(clean_query, primary)

        return IntentClassificationResult(
            query=clean_query,
            primary_intent=primary,
            secondary_intent=secondary,
            confidence=round(confidence, 2),
            intent_strength_score=strength,
            evidence=evidence,
        )

    def calculate_intent_strength(self, query: str, intent: SearchIntent) -> float:
        """
        Computes intent_strength_score (0.0 to 100.0).
        Vague queries (e.g. 'AI') get 20-30;
        Broad queries (e.g. 'AI tools') get 40-55;
        Specific long-tail queries (e.g. 'best AI tools for YouTube automation') get 85-95.
        """
        words = re.findall(r"\w+", query)
        num_words = len(words)

        # Baseline based on word count
        if num_words <= 1:
            base = 25.0
        elif num_words == 2:
            base = 45.0
        elif num_words == 3:
            base = 65.0
        elif num_words == 4:
            base = 78.0
        elif num_words <= 6:
            base = 88.0
        else:
            base = 94.0

        # Boost for high-intent modifier presence
        modifiers = [
            "how to", "best", "vs", "versus", "pricing", "tutorial", "alternative",
            "guide", "not working", "for", "step by step", "api", "review"
        ]
        q_lower = query.lower()
        modifier_count = sum(1 for m in modifiers if m in q_lower)
        modifier_boost = min(15.0, modifier_count * 5.0)

        # Specific audience or use-case markers
        use_case_markers = ["for beginners", "for creators", "for youtube", "for enterprise", "for small business", "for coding"]
        use_case_boost = 6.0 if any(u in q_lower for u in use_case_markers) else 0.0

        score = min(100.0, max(15.0, base + modifier_boost + use_case_boost))
        return round(score, 1)

    def validate_with_serp(
        self,
        initial_intent: SearchIntent,
        top_domains: list[str],
        result_types: list[str],
        is_official_dominant: bool,
    ) -> tuple[SearchIntent, float, str]:
        """
        Adjusts or validates predicted intent using actual SERP composition.
        If official domain or login/portal dominates, shifts towards NAVIGATIONAL.
        If video dominates, reinforces TUTORIAL/INFORMATIONAL.
        """
        if is_official_dominant and initial_intent != SearchIntent.NAVIGATIONAL:
            return (SearchIntent.NAVIGATIONAL, 0.92, "serp_dominated_by_official_portal")

        if result_types.count("video") >= 3 and initial_intent in (SearchIntent.INFORMATIONAL, SearchIntent.TUTORIAL):
            return (SearchIntent.TUTORIAL, 0.90, "serp_strongly_video_demonstration")

        return (initial_intent, 1.0, "serp_validates_predicted_intent")
