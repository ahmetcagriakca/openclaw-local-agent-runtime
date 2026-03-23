"""Context Assembler — D-040/D-041/D-042 artifact distribution engine."""
from context.artifact_identity import create_artifact_header, wrap_artifact
from context.summary_cache import SummaryCache, generate_basic_summary, generate_metadata_view
from datetime import datetime, timezone


class ContextAssembler:
    """Sits between Artifact Store and Mission Controller.

    D-040: Prevents repeated reads, delivers cheapest sufficient context.
    D-041: 5-tier delivery (A=metadata, B=summary, C=scoped, D=full, E=full+neighbors).
    D-042: Reread auto-downgrade + consumption logging.
    """

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.artifacts = {}           # artifactId -> full wrapped artifact
        self.summary_cache = SummaryCache()
        self.metadata_cache = {}      # artifactId -> metadata view
        self.consumption_log = []     # list of consumption records

    def store_artifact(self, artifact_type: str, data: dict,
                       stage_id: str, role: str, skill: str,
                       input_artifact_ids: list = None,
                       version: int = 1) -> str:
        """Store artifact with D-047 header. Returns artifactId."""
        header = create_artifact_header(
            artifact_type, data, self.mission_id,
            stage_id, role, skill, input_artifact_ids, version
        )
        wrapped = wrap_artifact(artifact_type, data, header)
        artifact_id = header.artifactId

        self.artifacts[artifact_id] = wrapped

        # Pre-generate summary and metadata
        summary = generate_basic_summary(wrapped)
        self.summary_cache.put(artifact_id, summary, "B")
        self.metadata_cache[artifact_id] = generate_metadata_view(wrapped)

        return artifact_id

    def get_artifact(self, artifact_id: str, requested_tier: str,
                     requesting_role: str, stage_id: str) -> dict | str | None:
        """Return artifact at requested tier.

        D-041: 5-tier delivery.
        D-042: Second full read auto-downgrades to summary.

        Tiers: A=metadata, B=summary, C=scoped, D=full, E=full+neighbors
        """
        if artifact_id not in self.artifacts:
            return None

        # D-042: Check for reread
        prior_full_reads = [
            c for c in self.consumption_log
            if c["artifactId"] == artifact_id
            and c["role"] == requesting_role
            and c["tier"] in ("D", "E")
        ]

        if prior_full_reads and requested_tier in ("D", "E"):
            # Second full read — downgrade to summary, log escalation
            self._log_consumption(artifact_id, requesting_role, stage_id,
                                  "B", reread=True,
                                  original_request=requested_tier)
            return self.summary_cache.get(artifact_id, "B")

        # Normal delivery
        self._log_consumption(artifact_id, requesting_role, stage_id,
                              requested_tier)

        if requested_tier == "A":
            return self.metadata_cache.get(artifact_id)
        elif requested_tier == "B":
            return self.summary_cache.get(artifact_id, "B")
        elif requested_tier == "C":
            # Scoped excerpt — for now return summary
            # Sprint 3+ will implement section extraction based on role context
            return self.summary_cache.get(artifact_id, "B")
        elif requested_tier == "D":
            return self.artifacts[artifact_id]
        elif requested_tier == "E":
            # Full + neighbors — return full for now
            # Sprint 4 (discovery map) will add neighbor file attachment
            return self.artifacts[artifact_id]

        return None

    def check_reread(self, artifact_id: str, role: str) -> bool:
        """Check if role has already done a full read of this artifact."""
        return any(
            c["artifactId"] == artifact_id
            and c["role"] == role
            and c["tier"] in ("D", "E")
            for c in self.consumption_log
        )

    def get_consumption_stats(self) -> dict:
        """Return consumption statistics for mission summary."""
        total = len(self.consumption_log)
        rereads = sum(1 for c in self.consumption_log if c.get("reread"))
        by_tier = {}
        for c in self.consumption_log:
            tier = c["tier"]
            by_tier[tier] = by_tier.get(tier, 0) + 1
        return {
            "total_reads": total,
            "rereads": rereads,
            "by_tier": by_tier,
            "cache_stats": self.summary_cache.stats()
        }

    def build_context_for_role(self, role: str, skill: str, stage_id: str,
                               artifact_ids: list,
                               tier_overrides: dict = None) -> list:
        """Build context package for a role using D-041 default tier matrix.

        Returns list of (artifactId, content, tier) tuples.
        """
        # D-041 default tiers per role
        role_defaults = {
            "product-owner": "B",
            "analyst": "D",
            "architect": "D",
            "project-manager": "B",
            "developer": "C",
            "tester": "C",
            "reviewer": "C",
            "manager": "B",
            "remote-operator": "D"
        }

        default_tier = role_defaults.get(role, "B")
        overrides = tier_overrides or {}

        context_package = []
        for aid in artifact_ids:
            tier = overrides.get(aid, default_tier)
            content = self.get_artifact(aid, tier, role, stage_id)
            context_package.append((aid, content, tier))

        return context_package

    def list_artifacts(self) -> list:
        """List all stored artifact IDs and types."""
        return [
            {
                "artifactId": aid,
                "artifactType": a.get("type"),
                "producedByRole": a.get("_artifact_header", {}).get("producedByRole"),
                "sizeTokens": a.get("_artifact_header", {}).get("sizeTokens")
            }
            for aid, a in self.artifacts.items()
        ]

    def _log_consumption(self, artifact_id, role, stage_id, tier,
                         reread=False, original_request=None):
        from context.policy_telemetry import emit_policy_event

        record = {
            "artifactId": artifact_id,
            "role": role,
            "stageId": stage_id,
            "tier": tier,
            "reread": reread,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if original_request:
            record["originalRequestedTier"] = original_request
            record["downgradedFrom"] = original_request
        self.consumption_log.append(record)

        # D-055: Telemetry emit
        if reread:
            emit_policy_event("context_reread", {
                "artifact_id": artifact_id, "role": role,
                "stage_id": stage_id, "original_requested_tier": original_request,
                "downgraded_to": tier, "mission_id": self.mission_id
            })
        else:
            emit_policy_event("context_read", {
                "artifact_id": artifact_id, "role": role,
                "stage_id": stage_id, "tier": tier,
                "mission_id": self.mission_id
            })
