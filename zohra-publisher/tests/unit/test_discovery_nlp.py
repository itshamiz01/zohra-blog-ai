"""Unit tests for NLP components: language, geography, entities, topics, and risk detection."""

from app.core.constants import RiskFlag
from app.discovery.nlp.entities import EntityExtractor
from app.discovery.nlp.geography import GeographyDetector
from app.discovery.nlp.language import LanguageDetector
from app.discovery.nlp.risk import RiskDetector
from app.discovery.nlp.topics import TopicClassifier


class TestLanguageDetector:
    def test_detects_english(self):
        text = "The quick brown fox jumps over the lazy dog and explores artificial intelligence."
        lang, conf = LanguageDetector.detect_language(text)
        assert lang == "en"
        assert conf >= 0.5

    def test_detects_hindi(self):
        text = "यह एक कृत्रिम बुद्धिमत्ता समाचार रिपोर्ट है जो तकनीक के बारे में बात करती है।"
        lang, conf = LanguageDetector.detect_language(text)
        assert lang == "hi"
        assert conf >= 0.8

    def test_detects_spanish(self):
        text = (
            "El nuevo modelo de inteligencia artificial fue lanzado hoy por la empresa tecnologica."
        )
        lang, conf = LanguageDetector.detect_language(text)
        assert lang == "es"
        assert conf >= 0.7

    def test_detects_japanese(self):
        text = "人工知能の新しいモデルが本日発表されました。"
        lang, conf = LanguageDetector.detect_language(text)
        assert lang == "ja"
        assert conf >= 0.8


class TestGeographyDetector:
    def test_detects_country_from_tld(self):
        country = GeographyDetector.detect_country(
            domain="bbc.co.uk", text="London authorities announce transport upgrades."
        )
        assert country == "GB"

    def test_detects_country_from_text_entities(self):
        country = GeographyDetector.detect_country(
            domain="techsite.com",
            text="The government in New Delhi announced a semiconductor mission in India.",
        )
        assert country == "IN"

    def test_defaults_to_global_when_no_strong_signal(self):
        country = GeographyDetector.detect_country(
            domain="cloudnative.io",
            text="Distributed systems architecture patterns for microservices.",
        )
        assert country == "global"


class TestEntityExtractor:
    def test_extracts_known_tech_entities(self):
        text = "OpenAI announced GPT-4o today with CEO Sam Altman in San Francisco."
        entities = EntityExtractor.extract_entities(text)
        names = [e["normalized_name"] for e in entities]
        assert "openai" in names
        assert "gpt_4" in names or "gpt-4" in names or "gpt-4o" in names
        assert "sam_altman" in names or "sam altman" in names

    def test_entity_canonical_normalization(self):
        assert EntityExtractor.normalize_canonical("OpenAI Inc.") == "OpenAI"
        assert EntityExtractor.normalize_canonical("Open AI") == "OpenAI"
        assert EntityExtractor.normalize_canonical("Google LLC") == "Google"
        assert EntityExtractor.normalize_canonical("Microsoft Corp") == "Microsoft"


class TestTopicClassifier:
    def test_classifies_technology_and_ai(self):
        text = "The new deep learning neural network framework optimizes GPU tensor operations."
        scores = TopicClassifier.classify(text)
        assert "Artificial Intelligence" in scores or "Technology" in scores
        assert (
            scores.get("Artificial Intelligence", 0.0) >= 0.5
            or scores.get("Technology", 0.0) >= 0.5
        )

    def test_classifies_finance(self):
        text = "Federal Reserve cuts interest rates by 25 basis points as inflation cools and markets rally."
        scores = TopicClassifier.classify(text)
        assert "Finance" in scores
        assert scores["Finance"] >= 0.5


class TestRiskDetector:
    def test_detects_medical_risk(self):
        text = "Clinical trial results show patient cancer vaccine treatment efficacy."
        flags, high_verif = RiskDetector.detect_risks(text)
        assert RiskFlag.MEDICAL in flags

    def test_detects_legal_and_allegation_with_person_protection(self):
        text = "John Doe was indicted by prosecutors on fraud charges and bribery allegations."
        flags, high_verif = RiskDetector.detect_risks(text)
        assert RiskFlag.LEGAL in flags or RiskFlag.ALLEGATION in flags or RiskFlag.CRIME in flags
        assert high_verif is True
