"""B-113: Docs-as-product pack tests."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

# Add tools/ to path
TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import generate_docs

# ── Fixtures ──────────────────────────────────────────────────────

MINIMAL_SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "Test", "version": "1.0.0"},
    "paths": {
        "/api/v1/missions": {
            "get": {
                "tags": ["missions"],
                "summary": "List all missions",
                "operationId": "list_missions",
                "parameters": [
                    {"name": "status", "in": "query",
                     "schema": {"type": "string"}, "required": False},
                ],
                "responses": {"200": {"description": "OK"}},
            },
            "post": {
                "tags": ["missions"],
                "summary": "Create mission",
                "operationId": "create_mission",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/CreateMissionRequest"},
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
        "/api/v1/health": {
            "get": {
                "tags": ["health"],
                "summary": "Health check",
                "operationId": "health",
                "responses": {"200": {"description": "OK"}},
            },
        },
    },
}


# ── API Reference Tests ──────────────────────────────────────────


class TestApiReferenceGeneration:
    """B-113: API reference markdown generation from OpenAPI spec."""

    def test_generates_markdown_string(self):
        result = generate_docs.generate_api_reference(MINIMAL_SPEC)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_title(self):
        result = generate_docs.generate_api_reference(MINIMAL_SPEC)
        assert "# Vezir Platform — API Reference" in result

    def test_contains_openapi_version(self):
        result = generate_docs.generate_api_reference(MINIMAL_SPEC)
        assert "3.1.0" in result

    def test_contains_endpoint_paths(self):
        result = generate_docs.generate_api_reference(MINIMAL_SPEC)
        assert "/api/v1/missions" in result
        assert "/api/v1/health" in result

    def test_contains_http_methods(self):
        result = generate_docs.generate_api_reference(MINIMAL_SPEC)
        assert "`GET`" in result
        assert "`POST`" in result

    def test_contains_summaries(self):
        result = generate_docs.generate_api_reference(MINIMAL_SPEC)
        assert "List all missions" in result
        assert "Create mission" in result
        assert "Health check" in result

    def test_contains_operation_ids(self):
        result = generate_docs.generate_api_reference(MINIMAL_SPEC)
        assert "list_missions" in result
        assert "create_mission" in result

    def test_groups_by_tag(self):
        result = generate_docs.generate_api_reference(MINIMAL_SPEC)
        assert "## missions" in result
        assert "## health" in result

    def test_contains_parameters(self):
        result = generate_docs.generate_api_reference(MINIMAL_SPEC)
        assert "status" in result
        assert "query" in result

    def test_contains_request_body(self):
        result = generate_docs.generate_api_reference(MINIMAL_SPEC)
        assert "CreateMissionRequest" in result

    def test_contains_responses(self):
        result = generate_docs.generate_api_reference(MINIMAL_SPEC)
        assert "`200`" in result
        assert "`201`" in result

    def test_total_endpoint_count(self):
        result = generate_docs.generate_api_reference(MINIMAL_SPEC)
        assert "**Total endpoints:** 3" in result

    def test_empty_spec_produces_output(self):
        empty = {"openapi": "3.1.0", "paths": {}}
        result = generate_docs.generate_api_reference(empty)
        assert "**Total endpoints:** 0" in result


# ── Architecture Tests ────────────���───────────────────────────────


class TestArchitectureGeneration:
    """B-113: Architecture overview generation."""

    def test_generates_markdown(self):
        result = generate_docs.generate_architecture()
        assert isinstance(result, str)
        assert "# Vezir Platform — Architecture Overview" in result

    def test_contains_component_map(self):
        result = generate_docs.generate_architecture()
        assert "Component Map" in result
        assert "Vezir UI (3000)" in result
        assert "Vezir API (8003)" in result

    def test_contains_port_map(self):
        result = generate_docs.generate_architecture()
        assert "3000" in result
        assert "8001" in result
        assert "8003" in result

    def test_contains_state_machine(self):
        result = generate_docs.generate_architecture()
        assert "Mission State Machine" in result
        assert "TIMED_OUT" in result

    def test_contains_specialist_roles(self):
        result = generate_docs.generate_architecture()
        assert "Specialist Roles (9)" in result
        assert "Planner" in result
        assert "Security" in result

    def test_contains_quality_gates(self):
        result = generate_docs.generate_architecture()
        assert "Quality Gates (3)" in result
        assert "G1" in result
        assert "G3" in result


# ── Onboarding Tests ─────────────────────────────────────────────


class TestOnboardingGeneration:
    """B-113: Developer onboarding guide generation."""

    def test_generates_markdown(self):
        result = generate_docs.generate_onboarding()
        assert isinstance(result, str)
        assert "# Vezir Platform — Developer Onboarding Guide" in result

    def test_contains_prerequisites(self):
        result = generate_docs.generate_onboarding()
        assert "Python" in result
        assert "Node.js" in result
        assert "Git" in result

    def test_contains_setup_steps(self):
        result = generate_docs.generate_onboarding()
        assert "pip install" in result
        assert "npm install" in result

    def test_contains_test_commands(self):
        result = generate_docs.generate_onboarding()
        assert "pytest" in result
        assert "vitest" in result
        assert "playwright" in result

    def test_contains_project_structure(self):
        result = generate_docs.generate_onboarding()
        assert "agent/" in result
        assert "frontend/" in result
        assert "config/" in result

    def test_contains_conventions(self):
        result = generate_docs.generate_onboarding()
        assert "atomic_write_json" in result
        assert "D-XXX" in result


# ── Integration: File Output Test ─���───────────────────────────────


class TestFileOutput:
    """B-113: End-to-end file generation."""

    def test_main_creates_three_files(self, tmp_path):
        # Create a minimal openapi.json
        spec_dir = tmp_path / "docs" / "api"
        spec_dir.mkdir(parents=True)
        (spec_dir / "openapi.json").write_text(
            json.dumps(MINIMAL_SPEC), encoding="utf-8")

        output_dir = tmp_path / "docs" / "generated"

        with patch.object(generate_docs, "OPENAPI_PATH", spec_dir / "openapi.json"), \
             patch.object(generate_docs, "OUTPUT_DIR", output_dir):
            generate_docs.main()

        assert (output_dir / "api-reference.md").exists()
        assert (output_dir / "architecture.md").exists()
        assert (output_dir / "onboarding.md").exists()

    def test_api_reference_file_not_empty(self, tmp_path):
        spec_dir = tmp_path / "docs" / "api"
        spec_dir.mkdir(parents=True)
        (spec_dir / "openapi.json").write_text(
            json.dumps(MINIMAL_SPEC), encoding="utf-8")

        output_dir = tmp_path / "docs" / "generated"

        with patch.object(generate_docs, "OPENAPI_PATH", spec_dir / "openapi.json"), \
             patch.object(generate_docs, "OUTPUT_DIR", output_dir):
            generate_docs.main()

        content = (output_dir / "api-reference.md").read_text(encoding="utf-8")
        assert len(content) > 100
        assert "List all missions" in content
