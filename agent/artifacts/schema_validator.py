"""Artifact schema validation — machine-readable schemas for all artifact types."""
import os

ARTIFACT_SCHEMAS = {
    "discovery_map": {
        "required_fields": ["repo_structure", "relevant_files",
                            "component_map", "working_set_recommendations"],
        "field_types": {
            "repo_structure": list,
            "relevant_files": list,
            "component_map": list,
            "working_set_recommendations": dict
        },
        "nested_required": {
            "relevant_files[]": ["path", "purpose", "relevance_score"],
            "component_map[]": ["component", "files", "responsibility"],
            "working_set_recommendations": ["developer", "tester", "reviewer"]
        }
    },
    "requirements_brief": {
        "required_fields": ["title", "summary", "requirements"],
        "field_types": {
            "title": str,
            "summary": str,
            "requirements": list
        },
        "nested_required": {
            "requirements[]": ["id", "description", "acceptance_criteria"]
        }
    },
    "analysis_report": {
        "required_fields": ["feasibility", "impact_analysis", "risks",
                            "effort_estimate", "recommendation"],
        "field_types": {
            "feasibility": str,
            "recommendation": str
        },
        "allowed_values": {
            "feasibility": ["high", "medium", "low"],
            "recommendation": ["proceed", "proceed_with_caution", "defer", "reject"]
        }
    },
    "test_report": {
        "required_fields": ["verdict"],
        "field_types": {
            "verdict": str
        },
        "allowed_values": {
            "verdict": ["pass", "conditional_pass", "fail"]
        }
    },
    "review_decision": {
        "required_fields": ["decision"],
        "field_types": {
            "decision": str
        },
        "allowed_values": {
            "decision": ["approve", "request_changes", "reject"]
        }
    },
    "code_delivery": {
        "required_fields": ["touched_files"],
        "field_types": {
            "touched_files": list
        }
    },
    "work_plan": {
        "required_fields": ["tasks"],
        "field_types": {
            "tasks": list
        },
        "nested_required": {
            "tasks[]": ["id", "description", "acceptance_criteria"]
        }
    },
    "recovery_decision": {
        "required_fields": ["diagnosis", "recovery_action"],
        "field_types": {
            "recovery_action": str
        },
        "allowed_values": {
            "recovery_action": ["retry_stage", "retry_from_stage_N",
                                "abort", "escalate_to_operator"]
        }
    }
}


def validate_artifact_data(artifact_type: str, data: dict) -> list[str]:
    """Validate artifact data against schema. Returns list of errors."""
    schema = ARTIFACT_SCHEMAS.get(artifact_type)
    if not schema:
        return []  # No schema = pass-through

    errors = []

    # Required fields
    for field in schema.get("required_fields", []):
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Field types
    for field, expected_type in schema.get("field_types", {}).items():
        if field in data and not isinstance(data[field], expected_type):
            errors.append(
                f"Field '{field}' expected {expected_type.__name__}, "
                f"got {type(data[field]).__name__}")

    # Allowed values
    for field, allowed in schema.get("allowed_values", {}).items():
        if field in data and data[field] not in allowed:
            errors.append(
                f"Field '{field}' value '{data[field]}' not in {allowed}")

    # Nested required fields
    for path, required in schema.get("nested_required", {}).items():
        if path.endswith("[]"):
            parent_field = path[:-2]
            if parent_field in data and isinstance(data[parent_field], list):
                for i, item in enumerate(data[parent_field]):
                    if isinstance(item, dict):
                        for req in required:
                            if req not in item:
                                errors.append(
                                    f"{parent_field}[{i}] missing '{req}'")
        else:
            if path in data and isinstance(data[path], dict):
                for req in required:
                    if req not in data[path]:
                        errors.append(f"{path} missing '{req}'")

    return errors


def extract_working_set_from_discovery(discovery_data: dict) -> dict:
    """Extract file targets from discovery_map for downstream roles.

    Returns: {developer: {readOnly, readWrite, creatable, directoryList},
              tester: {readOnly, directoryList},
              reviewer: {readOnly, directoryList}}
    """
    recs = discovery_data.get("working_set_recommendations", {})

    developer_files = recs.get("developer", [])
    tester_files = recs.get("tester", [])
    reviewer_files = recs.get("reviewer", [])

    return {
        "developer": {
            "readOnly": developer_files,
            "readWrite": [],
            "creatable": [],
            "directoryList": _extract_directories(developer_files)
        },
        "tester": {
            "readOnly": tester_files,
            "directoryList": _extract_directories(tester_files)
        },
        "reviewer": {
            "readOnly": reviewer_files,
            "directoryList": _extract_directories(reviewer_files)
        }
    }


def _extract_directories(file_paths: list) -> list:
    """Extract unique parent directories from file paths."""
    dirs = set()
    for path in file_paths:
        parent = os.path.dirname(path)
        if parent:
            dirs.add(parent)
    return sorted(dirs)
