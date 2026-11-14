"""Competition analysis and content gap detection package."""

from app.opportunity.competition.analyzer import (
    CompetitionAnalysisResult,
    CompetitionAnalyzer,
    DetectedGap,
)

__all__ = ["CompetitionAnalyzer", "CompetitionAnalysisResult", "DetectedGap"]
