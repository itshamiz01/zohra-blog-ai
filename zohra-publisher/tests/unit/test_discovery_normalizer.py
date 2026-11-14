"""Unit tests for URL normalization, content hashing, and SimHash deduplication."""

from app.discovery.dedup.detector import DeduplicationDetector
from app.discovery.normalizer.content import ContentNormalizer
from app.discovery.normalizer.url import URLNormalizer


class TestURLNormalizer:
    def test_strips_tracking_parameters(self):
        url = "https://example.com/article?utm_source=twitter&utm_medium=social&fbclid=12345&gclid=67890&id=42"
        canonical = URLNormalizer.normalize(url)
        assert "utm_source" not in canonical
        assert "fbclid" not in canonical
        assert "gclid" not in canonical
        assert "id=42" in canonical

    def test_normalizes_case_and_trailing_slash(self):
        url1 = "HTTPS://EXAMPLE.COM/PATH/"
        url2 = "https://example.com/path"
        assert URLNormalizer.normalize(url1) == URLNormalizer.normalize(url2)

    def test_strips_url_fragments(self):
        url = "https://example.com/guide#section-heading"
        canonical = URLNormalizer.normalize(url)
        assert "#" not in canonical
        assert canonical == "https://example.com/guide"

    def test_removes_default_ports(self):
        url1 = "https://example.com:443/article"
        url2 = "https://example.com/article"
        assert URLNormalizer.normalize(url1) == URLNormalizer.normalize(url2)


class TestContentNormalizer:
    def test_hashes_are_deterministic(self):
        text1 = "This is a detailed breaking news report."
        text2 = "This is a detailed breaking news report."
        h1 = ContentNormalizer.hash_content(text1)
        h2 = ContentNormalizer.hash_content(text2)
        assert h1 == h2
        assert len(h1) == 64

    def test_word_count_calculation(self):
        text = "OpenAI announced the release of its newest flagship model today."
        count = ContentNormalizer.count_words(text)
        assert count == 10

    def test_summary_extraction(self):
        long_text = (
            "Sentence one discusses the launch. "
            "Sentence two explains the pricing model. "
            "Sentence three details benchmark scores against competitors."
        )
        summary = ContentNormalizer.extract_summary(long_text, max_sentences=2)
        assert "Sentence one discusses the launch." in summary
        assert "Sentence two explains the pricing model." in summary
        assert "Sentence three" not in summary


class TestDeduplicationDetector:
    def test_simhash_identical_text(self):
        text = "Quantum computing research advances superconducting qubit coherence times significantly."
        sh1 = DeduplicationDetector.compute_simhash(text)
        sh2 = DeduplicationDetector.compute_simhash(text)
        assert sh1 == sh2
        assert DeduplicationDetector.hamming_distance(sh1, sh2) == 0

    def test_simhash_near_duplicate(self):
        text1 = (
            "OpenAI has officially launched GPT-4o today with multimodal voice and vision capabilities. "
            "The model is available immediately for all paid subscription tiers."
        )
        # Minor rewording
        text2 = (
            "OpenAI officially released GPT-4o today featuring multimodal voice and vision capabilities. "
            "The model is available now for all paid subscription tiers."
        )
        sh1 = DeduplicationDetector.compute_simhash(text1)
        sh2 = DeduplicationDetector.compute_simhash(text2)
        dist = DeduplicationDetector.hamming_distance(sh1, sh2)
        assert dist <= 10
        assert DeduplicationDetector.is_near_duplicate(sh1, sh2, max_hamming_distance=10)

    def test_simhash_unrelated_text(self):
        text1 = "NASA James Webb Space Telescope captures stunning infrared image of distant galaxy cluster."
        text2 = "Federal Reserve announces 25 basis point rate cut amid slowing inflation signals."
        sh1 = DeduplicationDetector.compute_simhash(text1)
        sh2 = DeduplicationDetector.compute_simhash(text2)
        dist = DeduplicationDetector.hamming_distance(sh1, sh2)
        assert dist > 10
        assert not DeduplicationDetector.is_near_duplicate(sh1, sh2)
