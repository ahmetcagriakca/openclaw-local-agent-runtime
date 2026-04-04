# Vezir Platform — API Reference

**Auto-generated:** 2026-04-04 10:02 UTC
**OpenAPI version:** 3.1.0
**Base URL:** `http://127.0.0.1:8003`

---

## Contents

- [admin](#admin) (6 endpoints)
- [agents](#agents) (4 endpoints)
- [alerts](#alerts) (6 endpoints)
- [approval-mutations](#approval-mutations) (2 endpoints)
- [approvals](#approvals) (2 endpoints)
- [artifacts](#artifacts) (2 endpoints)
- [cost](#cost) (3 endpoints)
- [dashboard](#dashboard) (4 endpoints)
- [dlq](#dlq) (6 endpoints)
- [events](#events) (1 endpoints)
- [features](#features) (1 endpoints)
- [health](#health) (2 endpoints)
- [logs](#logs) (1 endpoints)
- [mission-create](#mission-create) (1 endpoints)
- [mission-mutations](#mission-mutations) (5 endpoints)
- [missions](#missions) (8 endpoints)
- [policies](#policies) (7 endpoints)
- [roles](#roles) (1 endpoints)
- [schedules](#schedules) (7 endpoints)
- [signals](#signals) (1 endpoints)
- [telemetry](#telemetry) (1 endpoints)
- [telemetry-query](#telemetry-query) (5 endpoints)
- [templates](#templates) (7 endpoints)

---

## admin

| Method | Path | Summary |
|--------|------|---------|
| `POST` | `/api/v1/admin/backup` | Create Backup |
| `GET` | `/api/v1/admin/backups` | List Backups |
| `POST` | `/api/v1/admin/recovery/quarantine` | Quarantine Corrupted |
| `POST` | `/api/v1/admin/recovery/repair` | Repair Corrupted |
| `GET` | `/api/v1/admin/recovery/scan` | Scan Corruption |
| `POST` | `/api/v1/admin/restore` | Restore From Backup |

### `POST /api/v1/admin/backup`

> Create Backup

**Operation ID:** `create_backup_api_v1_admin_backup_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `include_missions` | query | boolean | No |
| `include_configs` | query | boolean | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/admin/backups`

> List Backups

**Operation ID:** `list_backups_api_v1_admin_backups_get`

**Responses:**

- `200`: Successful Response

---

### `POST /api/v1/admin/recovery/quarantine`

> Quarantine Corrupted

**Operation ID:** `quarantine_corrupted_api_v1_admin_recovery_quarantine_post`

**Responses:**

- `200`: Successful Response

---

### `POST /api/v1/admin/recovery/repair`

> Repair Corrupted

**Operation ID:** `repair_corrupted_api_v1_admin_recovery_repair_post`

**Responses:**

- `200`: Successful Response

---

### `GET /api/v1/admin/recovery/scan`

> Scan Corruption

**Operation ID:** `scan_corruption_api_v1_admin_recovery_scan_get`

**Responses:**

- `200`: Successful Response

---

### `POST /api/v1/admin/restore`

> Restore From Backup

**Operation ID:** `restore_from_backup_api_v1_admin_restore_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `backup_name` | query | string | Yes |
| `dry_run` | query | boolean | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## agents

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/agents/capability-matrix` | Capability Matrix |
| `GET` | `/api/v1/agents/performance` | Agent Performance |
| `GET` | `/api/v1/agents/providers` | List Providers |
| `GET` | `/api/v1/agents/roles` | List Agent Roles |

### `GET /api/v1/agents/capability-matrix`

> Capability Matrix

**Operation ID:** `capability_matrix_api_v1_agents_capability_matrix_get`

**Responses:**

- `200`: Successful Response

---

### `GET /api/v1/agents/performance`

> Agent Performance

**Operation ID:** `agent_performance_api_v1_agents_performance_get`

**Responses:**

- `200`: Successful Response

---

### `GET /api/v1/agents/providers`

> List Providers

**Operation ID:** `list_providers_api_v1_agents_providers_get`

**Responses:**

- `200`: Successful Response

---

### `GET /api/v1/agents/roles`

> List Agent Roles

**Operation ID:** `list_agent_roles_api_v1_agents_roles_get`

**Responses:**

- `200`: Successful Response

---

## alerts

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/alerts/active` | Get Active Alerts |
| `GET` | `/api/v1/alerts/history` | Get Alert History |
| `GET` | `/api/v1/alerts/rules` | List Rules |
| `POST` | `/api/v1/alerts/rules` | Create Rule |
| `GET` | `/api/v1/alerts/rules/{rule_id}` | Get Rule |
| `PUT` | `/api/v1/alerts/rules/{rule_id}` | Update Rule |

### `GET /api/v1/alerts/active`

> Get Active Alerts

**Operation ID:** `get_active_alerts_api_v1_alerts_active_get`

**Responses:**

- `200`: Successful Response

---

### `GET /api/v1/alerts/history`

> Get Alert History

**Operation ID:** `get_alert_history_api_v1_alerts_history_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `from` | query | string | No |
| `to` | query | string | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/alerts/rules`

> List Rules

**Operation ID:** `list_rules_api_v1_alerts_rules_get`

**Responses:**

- `200`: Successful Response

---

### `POST /api/v1/alerts/rules`

> Create Rule

**Operation ID:** `create_rule_api_v1_alerts_rules_post`

**Request Body:** `application/json` — `RuleCreate`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/alerts/rules/{rule_id}`

> Get Rule

**Operation ID:** `get_rule_api_v1_alerts_rules__rule_id__get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `rule_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /api/v1/alerts/rules/{rule_id}`

> Update Rule

**Operation ID:** `update_rule_api_v1_alerts_rules__rule_id__put`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `rule_id` | path | string | Yes |

**Request Body:** `application/json` — `RuleUpdate`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## approval-mutations

| Method | Path | Summary |
|--------|------|---------|
| `POST` | `/api/v1/approvals/{apv_id}/approve` | Approve Approval |
| `POST` | `/api/v1/approvals/{apv_id}/reject` | Reject Approval |

### `POST /api/v1/approvals/{apv_id}/approve`

> Approve Approval

**Operation ID:** `approve_approval_api_v1_approvals__apv_id__approve_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `apv_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `404`: Not Found
- `409`: Conflict
- `422`: Validation Error

---

### `POST /api/v1/approvals/{apv_id}/reject`

> Reject Approval

**Operation ID:** `reject_approval_api_v1_approvals__apv_id__reject_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `apv_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `404`: Not Found
- `409`: Conflict
- `422`: Validation Error

---

## approvals

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/approvals` | List Approvals |
| `GET` | `/api/v1/approvals/{apv_id}` | Get Approval |

### `GET /api/v1/approvals`

> List Approvals

**Operation ID:** `list_approvals_api_v1_approvals_get`

**Responses:**

- `200`: Successful Response

---

### `GET /api/v1/approvals/{apv_id}`

> Get Approval

**Operation ID:** `get_approval_api_v1_approvals__apv_id__get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `apv_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `404`: Not Found
- `422`: Validation Error

---

## artifacts

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/missions/{mission_id}/artifacts` | List Artifacts |
| `GET` | `/api/v1/missions/{mission_id}/artifacts/{artifact_id}` | Get Artifact |

### `GET /api/v1/missions/{mission_id}/artifacts`

> List Artifacts

**Operation ID:** `list_artifacts_api_v1_missions__mission_id__artifacts_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/missions/{mission_id}/artifacts/{artifact_id}`

> Get Artifact

**Operation ID:** `get_artifact_api_v1_missions__mission_id__artifacts__artifact_id__get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |
| `artifact_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## cost

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/cost/missions` | Cost Per Mission |
| `GET` | `/api/v1/cost/summary` | Cost Summary |
| `GET` | `/api/v1/cost/trends` | Cost Trends |

### `GET /api/v1/cost/missions`

> Cost Per Mission

**Operation ID:** `cost_per_mission_api_v1_cost_missions_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `limit` | query | integer | No |
| `offset` | query | integer | No |
| `sort` | query | string | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/cost/summary`

> Cost Summary

**Operation ID:** `cost_summary_api_v1_cost_summary_get`

**Responses:**

- `200`: Successful Response

---

### `GET /api/v1/cost/trends`

> Cost Trends

**Operation ID:** `cost_trends_api_v1_cost_trends_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `bucket` | query | string | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## dashboard

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/dashboard/live` | Dashboard Live |
| `GET` | `/api/v1/dashboard/missions` | List Dashboard Missions |
| `GET` | `/api/v1/dashboard/missions/{mission_id}` | Get Dashboard Mission |
| `GET` | `/api/v1/dashboard/summary` | Get Dashboard Summary |

### `GET /api/v1/dashboard/live`

> Dashboard Live

**Operation ID:** `dashboard_live_api_v1_dashboard_live_get`

**Responses:**

- `200`: Successful Response

---

### `GET /api/v1/dashboard/missions`

> List Dashboard Missions

**Operation ID:** `list_dashboard_missions_api_v1_dashboard_missions_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `status` | query | string | No |
| `complexity` | query | string | No |
| `search` | query | string | No |
| `from` | query | string | No |
| `to` | query | string | No |
| `limit` | query | integer | No |
| `offset` | query | integer | No |
| `sort` | query | string | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/dashboard/missions/{mission_id}`

> Get Dashboard Mission

**Operation ID:** `get_dashboard_mission_api_v1_dashboard_missions__mission_id__get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/dashboard/summary`

> Get Dashboard Summary

**Operation ID:** `get_dashboard_summary_api_v1_dashboard_summary_get`

**Responses:**

- `200`: Successful Response

---

## dlq

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/dlq` | List Dlq |
| `POST` | `/api/v1/dlq/purge-resolved` | Purge Resolved |
| `GET` | `/api/v1/dlq/summary` | Dlq Summary |
| `DELETE` | `/api/v1/dlq/{dlq_id}` | Purge Dlq Entry |
| `GET` | `/api/v1/dlq/{dlq_id}` | Get Dlq Entry |
| `POST` | `/api/v1/dlq/{dlq_id}/retry` | Retry Dlq Entry |

### `GET /api/v1/dlq`

> List Dlq

**Operation ID:** `list_dlq_api_v1_dlq_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `status` | query | string | No |
| `limit` | query | integer | No |
| `offset` | query | integer | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `POST /api/v1/dlq/purge-resolved`

> Purge Resolved

**Operation ID:** `purge_resolved_api_v1_dlq_purge_resolved_post`

**Responses:**

- `200`: Successful Response

---

### `GET /api/v1/dlq/summary`

> Dlq Summary

**Operation ID:** `dlq_summary_api_v1_dlq_summary_get`

**Responses:**

- `200`: Successful Response

---

### `DELETE /api/v1/dlq/{dlq_id}`

> Purge Dlq Entry

**Operation ID:** `purge_dlq_entry_api_v1_dlq__dlq_id__delete`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `dlq_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/dlq/{dlq_id}`

> Get Dlq Entry

**Operation ID:** `get_dlq_entry_api_v1_dlq__dlq_id__get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `dlq_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `POST /api/v1/dlq/{dlq_id}/retry`

> Retry Dlq Entry

**Operation ID:** `retry_dlq_entry_api_v1_dlq__dlq_id__retry_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `dlq_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## events

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/events/stream` | Sse Stream |

### `GET /api/v1/events/stream`

> Sse Stream

**Operation ID:** `sse_stream_api_v1_events_stream_get`

**Responses:**

- `200`: Successful Response

---

## features

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/features` | List Features |

### `GET /api/v1/features`

> List Features

**Operation ID:** `list_features_api_v1_features_get`

**Responses:**

- `200`: Successful Response

---

## health

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/capabilities` | List Capabilities |
| `GET` | `/api/v1/health` | Get Health |

### `GET /api/v1/capabilities`

> List Capabilities

**Operation ID:** `list_capabilities_api_v1_capabilities_get`

**Responses:**

- `200`: Successful Response

---

### `GET /api/v1/health`

> Get Health

**Operation ID:** `get_health_api_v1_health_get`

**Responses:**

- `200`: Successful Response

---

## logs

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/logs/recent` | Get Recent Logs |

### `GET /api/v1/logs/recent`

> Get Recent Logs

**Operation ID:** `get_recent_logs_api_v1_logs_recent_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `limit` | query | integer | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## mission-create

| Method | Path | Summary |
|--------|------|---------|
| `POST` | `/api/v1/missions` | Create Mission |

### `POST /api/v1/missions`

> Create Mission

**Operation ID:** `create_mission_api_v1_missions_post`

**Request Body:** `application/json` — `CreateMissionRequest`

**Responses:**

- `201`: Successful Response
- `422`: Validation Error

---

## mission-mutations

| Method | Path | Summary |
|--------|------|---------|
| `POST` | `/api/v1/missions/{mission_id}/cancel` | Cancel Mission |
| `POST` | `/api/v1/missions/{mission_id}/pause` | Pause Mission |
| `POST` | `/api/v1/missions/{mission_id}/resume` | Resume Mission |
| `POST` | `/api/v1/missions/{mission_id}/retry` | Retry Mission |
| `POST` | `/api/v1/missions/{mission_id}/skip-stage` | Skip Stage |

### `POST /api/v1/missions/{mission_id}/cancel`

> Cancel Mission

**Operation ID:** `cancel_mission_api_v1_missions__mission_id__cancel_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `404`: Not Found
- `409`: Conflict
- `422`: Validation Error

---

### `POST /api/v1/missions/{mission_id}/pause`

> Pause Mission

**Operation ID:** `pause_mission_api_v1_missions__mission_id__pause_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `404`: Not Found
- `409`: Conflict
- `422`: Validation Error

---

### `POST /api/v1/missions/{mission_id}/resume`

> Resume Mission

**Operation ID:** `resume_mission_api_v1_missions__mission_id__resume_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `404`: Not Found
- `409`: Conflict
- `422`: Validation Error

---

### `POST /api/v1/missions/{mission_id}/retry`

> Retry Mission

**Operation ID:** `retry_mission_api_v1_missions__mission_id__retry_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `404`: Not Found
- `409`: Conflict
- `422`: Validation Error

---

### `POST /api/v1/missions/{mission_id}/skip-stage`

> Skip Stage

**Operation ID:** `skip_stage_api_v1_missions__mission_id__skip_stage_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `404`: Not Found
- `409`: Conflict
- `422`: Validation Error

---

## missions

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/missions` | List Missions |
| `GET` | `/api/v1/missions/replay/list` | List Replayable |
| `GET` | `/api/v1/missions/replay/{mission_id}` | Replay Mission |
| `GET` | `/api/v1/missions/replay/{mission_id}/fixture` | Generate Fixture |
| `GET` | `/api/v1/missions/{mission_id}` | Get Mission |
| `GET` | `/api/v1/missions/{mission_id}/stages` | Get Mission Stages |
| `GET` | `/api/v1/missions/{mission_id}/stages/{stage_idx}` | Get Mission Stage |
| `GET` | `/api/v1/missions/{mission_id}/token-report` | Get Token Report |

### `GET /api/v1/missions`

> List Missions

**Operation ID:** `list_missions_api_v1_missions_get`

**Responses:**

- `200`: Successful Response

---

### `GET /api/v1/missions/replay/list`

> List Replayable

**Operation ID:** `list_replayable_api_v1_missions_replay_list_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `limit` | query | integer | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/missions/replay/{mission_id}`

> Replay Mission

**Operation ID:** `replay_mission_api_v1_missions_replay__mission_id__get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/missions/replay/{mission_id}/fixture`

> Generate Fixture

**Operation ID:** `generate_fixture_api_v1_missions_replay__mission_id__fixture_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/missions/{mission_id}`

> Get Mission

**Operation ID:** `get_mission_api_v1_missions__mission_id__get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `404`: Not Found
- `422`: Validation Error

---

### `GET /api/v1/missions/{mission_id}/stages`

> Get Mission Stages

**Operation ID:** `get_mission_stages_api_v1_missions__mission_id__stages_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/missions/{mission_id}/stages/{stage_idx}`

> Get Mission Stage

**Operation ID:** `get_mission_stage_api_v1_missions__mission_id__stages__stage_idx__get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |
| `stage_idx` | path | integer | Yes |

**Responses:**

- `200`: Successful Response
- `404`: Not Found
- `422`: Validation Error

---

### `GET /api/v1/missions/{mission_id}/token-report`

> Get Token Report

**Operation ID:** `get_token_report_api_v1_missions__mission_id__token_report_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `404`: Not Found
- `422`: Validation Error

---

## policies

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/policies` | List Policies |
| `POST` | `/api/v1/policies` | Create Policy |
| `GET` | `/api/v1/policies/context-schema` | Get Policy Context Schema |
| `POST` | `/api/v1/policies/reload` | Reload Policies |
| `DELETE` | `/api/v1/policies/{name}` | Delete Policy |
| `GET` | `/api/v1/policies/{name}` | Get Policy |
| `PUT` | `/api/v1/policies/{name}` | Update Policy |

### `GET /api/v1/policies`

> List Policies

**Operation ID:** `list_policies_api_v1_policies_get`

**Responses:**

- `200`: Successful Response

---

### `POST /api/v1/policies`

> Create Policy

**Operation ID:** `create_policy_api_v1_policies_post`

**Request Body:** `application/json` — `object`

**Responses:**

- `201`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/policies/context-schema`

> Get Policy Context Schema

**Operation ID:** `get_policy_context_schema_api_v1_policies_context_schema_get`

**Responses:**

- `200`: Successful Response

---

### `POST /api/v1/policies/reload`

> Reload Policies

**Operation ID:** `reload_policies_api_v1_policies_reload_post`

**Responses:**

- `200`: Successful Response

---

### `DELETE /api/v1/policies/{name}`

> Delete Policy

**Operation ID:** `delete_policy_api_v1_policies__name__delete`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `name` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/policies/{name}`

> Get Policy

**Operation ID:** `get_policy_api_v1_policies__name__get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `name` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /api/v1/policies/{name}`

> Update Policy

**Operation ID:** `update_policy_api_v1_policies__name__put`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `name` | path | string | Yes |

**Request Body:** `application/json` — `object`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## roles

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/roles` | List Roles |

### `GET /api/v1/roles`

> List Roles

**Operation ID:** `list_roles_api_v1_roles_get`

**Responses:**

- `200`: Successful Response

---

## schedules

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/schedules` | List Schedules |
| `POST` | `/api/v1/schedules` | Create Schedule |
| `DELETE` | `/api/v1/schedules/{schedule_id}` | Delete Schedule |
| `GET` | `/api/v1/schedules/{schedule_id}` | Get Schedule |
| `PUT` | `/api/v1/schedules/{schedule_id}` | Update Schedule |
| `POST` | `/api/v1/schedules/{schedule_id}/run` | Run Schedule Now |
| `POST` | `/api/v1/schedules/{schedule_id}/toggle` | Toggle Schedule |

### `GET /api/v1/schedules`

> List Schedules

**Operation ID:** `list_schedules_api_v1_schedules_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `enabled_only` | query | boolean | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `POST /api/v1/schedules`

> Create Schedule

**Operation ID:** `create_schedule_api_v1_schedules_post`

**Request Body:** `application/json` — `CreateScheduleRequest`

**Responses:**

- `201`: Successful Response
- `422`: Validation Error

---

### `DELETE /api/v1/schedules/{schedule_id}`

> Delete Schedule

**Operation ID:** `delete_schedule_api_v1_schedules__schedule_id__delete`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `schedule_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/schedules/{schedule_id}`

> Get Schedule

**Operation ID:** `get_schedule_api_v1_schedules__schedule_id__get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `schedule_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /api/v1/schedules/{schedule_id}`

> Update Schedule

**Operation ID:** `update_schedule_api_v1_schedules__schedule_id__put`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `schedule_id` | path | string | Yes |

**Request Body:** `application/json` — `UpdateScheduleRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `POST /api/v1/schedules/{schedule_id}/run`

> Run Schedule Now

**Operation ID:** `run_schedule_now_api_v1_schedules__schedule_id__run_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `schedule_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `POST /api/v1/schedules/{schedule_id}/toggle`

> Toggle Schedule

**Operation ID:** `toggle_schedule_api_v1_schedules__schedule_id__toggle_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `schedule_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## signals

| Method | Path | Summary |
|--------|------|---------|
| `DELETE` | `/api/v1/signals/{request_id}` | Delete Signal |

### `DELETE /api/v1/signals/{request_id}`

> Delete Signal

**Operation ID:** `delete_signal_api_v1_signals__request_id__delete`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `request_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `404`: Not Found
- `422`: Validation Error

---

## telemetry

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/telemetry` | List Telemetry |

### `GET /api/v1/telemetry`

> List Telemetry

**Operation ID:** `list_telemetry_api_v1_telemetry_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | query | string | No |
| `limit` | query | integer | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## telemetry-query

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/telemetry/logs` | Query Logs |
| `GET` | `/api/v1/telemetry/metrics/current` | Get Current Metrics |
| `GET` | `/api/v1/telemetry/metrics/history` | Get Metric History |
| `GET` | `/api/v1/telemetry/traces` | List Traces |
| `GET` | `/api/v1/telemetry/traces/{mission_id}` | Get Trace |

### `GET /api/v1/telemetry/logs`

> Query Logs

**Operation ID:** `query_logs_api_v1_telemetry_logs_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | query | string | No |
| `level` | query | string | No |
| `event` | query | string | No |
| `stage` | query | string | No |
| `search` | query | string | No |
| `from` | query | string | No |
| `to` | query | string | No |
| `limit` | query | integer | No |
| `offset` | query | integer | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/telemetry/metrics/current`

> Get Current Metrics

**Operation ID:** `get_current_metrics_api_v1_telemetry_metrics_current_get`

**Responses:**

- `200`: Successful Response

---

### `GET /api/v1/telemetry/metrics/history`

> Get Metric History

**Operation ID:** `get_metric_history_api_v1_telemetry_metrics_history_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `from` | query | string | No |
| `to` | query | string | No |
| `limit` | query | integer | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/telemetry/traces`

> List Traces

**Operation ID:** `list_traces_api_v1_telemetry_traces_get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `from` | query | string | No |
| `to` | query | string | No |
| `limit` | query | integer | No |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/telemetry/traces/{mission_id}`

> Get Trace

**Operation ID:** `get_trace_api_v1_telemetry_traces__mission_id__get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `mission_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## templates

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/api/v1/templates` | List Templates |
| `POST` | `/api/v1/templates` | Create Template |
| `GET` | `/api/v1/templates/presets` | List Presets |
| `DELETE` | `/api/v1/templates/{template_id}` | Delete Template |
| `GET` | `/api/v1/templates/{template_id}` | Get Template |
| `PUT` | `/api/v1/templates/{template_id}` | Update Template |
| `POST` | `/api/v1/templates/{template_id}/run` | Run Template |

### `GET /api/v1/templates`

> List Templates

**Operation ID:** `list_templates_api_v1_templates_get`

**Responses:**

- `200`: Successful Response

---

### `POST /api/v1/templates`

> Create Template

**Operation ID:** `create_template_api_v1_templates_post`

**Request Body:** `application/json` — `CreateTemplateRequest`

**Responses:**

- `201`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/templates/presets`

> List Presets

**Operation ID:** `list_presets_api_v1_templates_presets_get`

**Responses:**

- `200`: Successful Response

---

### `DELETE /api/v1/templates/{template_id}`

> Delete Template

**Operation ID:** `delete_template_api_v1_templates__template_id__delete`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `template_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `GET /api/v1/templates/{template_id}`

> Get Template

**Operation ID:** `get_template_api_v1_templates__template_id__get`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `template_id` | path | string | Yes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /api/v1/templates/{template_id}`

> Update Template

**Operation ID:** `update_template_api_v1_templates__template_id__put`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `template_id` | path | string | Yes |

**Request Body:** `application/json` — `UpdateTemplateRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### `POST /api/v1/templates/{template_id}/run`

> Run Template

**Operation ID:** `run_template_api_v1_templates__template_id__run_post`

**Parameters:**

| Name | In | Type | Required |
|------|----|------|----------|
| `template_id` | path | string | Yes |

**Request Body:** `application/json` — `RunTemplateRequest`

**Responses:**

- `201`: Successful Response
- `422`: Validation Error

---

**Total endpoints:** 83
