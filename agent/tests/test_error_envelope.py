"""Tests for Sprint 50 RFC 9457 Error Envelope.

Covers: error model, error codes, global handler, backward compat.
"""

from api.error_envelope import _build_error_response


class TestErrorModel:
    def test_envelope_has_required_fields(self):
        body = _build_error_response(404, "Not found")
        assert "type" in body
        assert "title" in body
        assert "status" in body
        assert "detail" in body
        assert "instance" in body
        assert "timestamp" in body

    def test_envelope_status_matches(self):
        body = _build_error_response(422, "Invalid input")
        assert body["status"] == 422

    def test_envelope_detail_preserved(self):
        """Backward compat: detail field still present."""
        body = _build_error_response(404, "Policy rule 'x' not found")
        assert body["detail"] == "Policy rule 'x' not found"

    def test_envelope_type_format(self):
        body = _build_error_response(404, "not found")
        assert body["type"].startswith("about:blank#")

    def test_envelope_instance(self):
        body = _build_error_response(404, "not found", instance="/api/v1/policies/x")
        assert body["instance"] == "/api/v1/policies/x"


class TestErrorCodes:
    def test_404_maps_to_not_found(self):
        body = _build_error_response(404, "x")
        assert "not_found" in body["type"]

    def test_422_maps_to_validation_error(self):
        body = _build_error_response(422, "x")
        assert "validation_error" in body["type"]

    def test_409_maps_to_conflict(self):
        body = _build_error_response(409, "x")
        assert "conflict" in body["type"]

    def test_429_maps_to_rate_limited(self):
        body = _build_error_response(429, "x")
        assert "rate_limited" in body["type"]

    def test_500_maps_to_internal(self):
        body = _build_error_response(500, "x")
        assert "internal_error" in body["type"]

    def test_custom_error_code(self):
        body = _build_error_response(418, "teapot", error_code="teapot")
        assert "teapot" in body["type"]


class TestBackwardCompat:
    def test_old_detail_field_still_works(self):
        """Existing clients parse 'detail' — must still be present."""
        body = _build_error_response(404, "Policy rule 'test' not found")
        assert body["detail"] == "Policy rule 'test' not found"
        assert body["status"] == 404

    def test_timestamp_is_iso(self):
        body = _build_error_response(500, "err")
        assert "T" in body["timestamp"]
        assert body["timestamp"].endswith("+00:00") or body["timestamp"].endswith("Z")
