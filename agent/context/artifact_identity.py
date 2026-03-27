"""Artifact identity — D-047 compliant headers for typed artifacts."""
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass
class ArtifactHeader:
    """D-047 artifact identity header."""
    artifactId: str
    artifactType: str
    version: int
    missionId: str
    producedByStage: str
    producedByRole: str
    producedBySkill: str
    producedAt: str
    inputArtifactIds: list
    contentHash: str
    sizeTokens: int
    compressionAvailable: dict


def create_artifact_header(
    artifact_type: str,
    data: dict,
    mission_id: str,
    stage_id: str,
    role: str,
    skill: str,
    input_artifact_ids: list = None,
    version: int = 1
) -> ArtifactHeader:
    """Create D-047 compliant artifact identity header."""
    content_bytes = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    content_hash = hashlib.sha256(content_bytes).hexdigest()
    token_estimate = max(1, len(content_bytes) // 4)
    timestamp = datetime.now(timezone.utc)

    return ArtifactHeader(
        artifactId=f"art-{timestamp.strftime('%Y%m%d%H%M%S%f')}-{stage_id}-{role}",
        artifactType=artifact_type,
        version=version,
        missionId=mission_id,
        producedByStage=stage_id,
        producedByRole=role,
        producedBySkill=skill,
        producedAt=timestamp.isoformat(),
        inputArtifactIds=input_artifact_ids or [],
        contentHash=f"sha256:{content_hash}",
        sizeTokens=token_estimate,
        compressionAvailable={}
    )


def wrap_artifact(artifact_type: str, data: dict, header: ArtifactHeader) -> dict:
    """Wrap data with D-047 header into a complete artifact."""
    return {
        "_artifact_header": asdict(header),
        "type": artifact_type,
        "data": data
    }


def validate_artifact_header(artifact: dict) -> list:
    """Validate artifact has all required D-047 header fields. Returns error list."""
    required = [
        "artifactId", "artifactType", "version", "missionId",
        "producedByStage", "producedByRole", "producedBySkill",
        "inputArtifactIds", "contentHash", "compressionAvailable"
    ]
    header = artifact.get("_artifact_header")
    if not header:
        return ["Missing _artifact_header"]
    return [f"Missing field: {f}" for f in required if f not in header]
