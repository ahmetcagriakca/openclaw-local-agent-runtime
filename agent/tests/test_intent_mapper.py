"""Tests for intent mapper (B-019, Sprint 56)."""
import pytest

from mission.intent_mapper import IntentMapper, classify_intent, classify_with_fallback, get_mapper


@pytest.fixture
def mapper():
    return IntentMapper()


class TestIntentMapperClassify:
    def test_status_check_turkish(self, mapper):
        result = mapper.classify("sistem durumu kontrol et")
        assert result is not None
        assert result["intent"] == "status_check"

    def test_status_check_english(self, mapper):
        result = mapper.classify("system status check")
        assert result is not None
        assert result["intent"] == "status_check"

    def test_code_change_detected(self, mapper):
        result = mapper.classify("refactor the service")
        assert result is not None
        assert result["intent"] == "code_change"

    def test_test_run_detected(self, mapper):
        result = mapper.classify("testleri çalıştır")
        assert result is not None
        assert result["intent"] == "test_run"

    def test_deployment_detected(self, mapper):
        result = mapper.classify("prod ortama deploy et")
        assert result is not None
        assert result["intent"] == "deployment"

    def test_security_audit_detected(self, mapper):
        result = mapper.classify("güvenlik taraması yap")
        assert result is not None
        assert result["intent"] == "security_audit"

    def test_documentation_detected(self, mapper):
        result = mapper.classify("api dokümantasyon oluştur")
        assert result is not None
        assert result["intent"] == "documentation"

    def test_analysis_detected(self, mapper):
        result = mapper.classify("performans analizi yap")
        assert result is not None
        assert result["intent"] == "analysis"

    def test_infrastructure_detected(self, mapper):
        result = mapper.classify("docker container kur")
        assert result is not None
        assert result["intent"] == "infrastructure"

    def test_no_match_returns_none(self, mapper):
        result = mapper.classify("merhaba dünya")
        assert result is None

    def test_empty_message_returns_none(self, mapper):
        result = mapper.classify("")
        assert result is None

    def test_confidence_score(self, mapper):
        result = mapper.classify("sistem durumu")
        assert result is not None
        assert 0 < result["confidence"] <= 1.0

    def test_tags_present(self, mapper):
        result = mapper.classify("sistem durumu")
        assert "tags" in result
        assert isinstance(result["tags"], list)


class TestIntentMapperComplexityOverride:
    def test_status_trivial_override(self, mapper):
        result = mapper.classify("sistem durumu")
        assert result["complexity_override"] == "trivial"

    def test_deployment_complex_override(self, mapper):
        result = mapper.classify("production deploy")
        assert result["complexity_override"] == "complex"

    def test_code_change_no_override(self, mapper):
        result = mapper.classify("refactor the main module")
        assert result is not None
        assert result["complexity_override"] is None

    def test_test_run_simple_override(self, mapper):
        result = mapper.classify("pytest çalıştır")
        assert result["complexity_override"] == "simple"


class TestIntentMapperWithFallback:
    def test_fallback_with_intent_override(self):
        result = classify_with_fallback("sistem durumu kontrol et")
        assert result["source"] == "intent_override"
        assert result["complexity"]["complexity"] == "trivial"

    def test_fallback_without_intent(self):
        result = classify_with_fallback("bu mesaj hiçbir intent'e uymuyor")
        assert result["source"] == "complexity_router"
        assert result["intent"] is None

    def test_fallback_intent_no_override(self):
        result = classify_with_fallback("refactor the main module")
        if result["intent"] is not None:
            assert result["source"] == "complexity_router"


class TestIntentMapperCustomRules:
    def test_custom_rules(self):
        rules = [
            {
                "intent": "greeting",
                "description": "Greeting message",
                "patterns": [r"merhaba|hello|hi"],
                "complexity_override": "trivial",
                "tags": ["social"],
            }
        ]
        mapper = IntentMapper(rules=rules)
        result = mapper.classify("merhaba nasılsın")
        assert result["intent"] == "greeting"

    def test_empty_rules(self):
        mapper = IntentMapper(rules=[])
        result = mapper.classify("anything")
        assert result is None


class TestIntentMapperListIntents:
    def test_list_intents(self, mapper):
        intents = mapper.list_intents()
        assert len(intents) == 8
        names = [i["intent"] for i in intents]
        assert "status_check" in names
        assert "code_change" in names
        assert "deployment" in names

    def test_list_intents_structure(self, mapper):
        intents = mapper.list_intents()
        for intent in intents:
            assert "intent" in intent
            assert "description" in intent
            assert "pattern_count" in intent
            assert intent["pattern_count"] > 0


class TestConvenienceFunctions:
    def test_classify_intent(self):
        result = classify_intent("sistem durumu")
        assert result is not None
        assert result["intent"] == "status_check"

    def test_get_mapper_singleton(self):
        m1 = get_mapper()
        m2 = get_mapper()
        assert m1 is m2

    def test_classify_with_fallback_function(self):
        result = classify_with_fallback("deploy to production")
        assert "intent" in result
        assert "complexity" in result
