/**
 * TypeScript type definitions — 1:1 mapping from agent/api/schemas.py.
 * D-067: schemas FROZEN (additive-only post-freeze).
 * D-082: manual TS types from frozen Pydantic schemas.
 */

// ── D-068: Data Quality States (6-state, D-079) ────────────────

export enum DataQualityStatus {
  Fresh = 'fresh',
  Partial = 'partial',
  Stale = 'stale',
  Degraded = 'degraded',
  Unknown = 'unknown',
  NotReached = 'not_reached',
}

export enum MissionState {
  Pending = 'pending',
  Planning = 'planning',
  Executing = 'executing',
  GateCheck = 'gate_check',
  Rework = 'rework',
  ApprovalWait = 'approval_wait',
  Completed = 'completed',
  Failed = 'failed',
  Aborted = 'aborted',
  TimedOut = 'timed_out',
}

export enum CapabilityStatus {
  Available = 'available',
  Unavailable = 'unavailable',
  Unknown = 'unknown',
}

// ── Source & Freshness ──────────────────────────────────────────

export interface SourceInfo {
  name: string
  ageMs: number
  status: DataQualityStatus
}

export interface ResponseMeta {
  freshnessMs: number
  dataQuality: DataQualityStatus
  sourcesUsed: SourceInfo[]
  sourcesMissing: string[]
  generatedAt: string
}

// ── Gate & Findings ─────────────────────────────────────────────

export interface Finding {
  check: string
  status: string // 'pass' | 'fail' | 'warn'
  detail: string
}

export interface GateResultDetail {
  gateName: string
  passed: boolean
  findings: Finding[]
}

// ── Stage ───────────────────────────────────────────────────────

export interface StageDetail {
  index: number
  role: string
  agentUsed: string | null
  status: string
  error: string | null
  result: string | null
  systemPrompt: string | null
  userPrompt: string | null
  turnsUsed: number
  gateResults: GateResultDetail | null
  denyForensics: Record<string, unknown> | null
  isRework: boolean
  reworkCycle: number
  isRecovery: boolean
  toolCalls: number
  policyDenies: number
  durationMs: number | null
  startedAt: string | null
  finishedAt: string | null
}

// ── Mission ─────────────────────────────────────────────────────

export interface StateTransition {
  from: string
  to: string
  reason: string
  timestamp: string
}

export interface SignalArtifact {
  requestId: string
  type: string
  targetId: string
  missionId: string
  requestedAt: string
  source: string
  ageSeconds: number
}

export interface MissionSummary {
  missionId: string
  state: string
  goal: string | null
  complexity: string | null
  error: string | null
  stages: StageDetail[]
  denyForensics: Record<string, unknown>[]
  pendingSignals: SignalArtifact[]
  totalPolicyDenies: number
  artifactCount: number
  totalDurationMs: number | null
  startedAt: string | null
  completedAt: string | null
  finalState: string | null
  stateTransitions: StateTransition[]
}

export interface MissionListItem {
  missionId: string
  state: string
  goal: string | null
  dataQuality: DataQualityStatus
  startedAt: string | null
  stageCount: number
  currentStage: number
  stageSummary: string
}

// ── Capability ──────────────────────────────────────────────────

export interface CapabilityEntry {
  name: string
  status: CapabilityStatus
  since: string | null
  detail: string | null
}

// ── Health ──────────────────────────────────────────────────────

export interface ComponentHealth {
  name: string
  status: string // 'ok' | 'degraded' | 'error' | 'unknown'
  lastCheckAt: string | null
  detail: string | null
}

// ── Approval ────────────────────────────────────────────────────

export interface ApprovalEntry {
  id: string
  missionId: string | null
  toolName: string | null
  risk: string | null
  status: string
  requestedAt: string | null
  respondedAt: string | null
}

// ── Telemetry ───────────────────────────────────────────────────

export interface TelemetryEntry {
  type: string
  timestamp: string | null
  missionId: string | null
  sourceFile: string
  data: Record<string, unknown>
}

// ── Response Wrappers (GPT Fix 3) ──────────────────────────────

export interface MissionDetailResponse {
  meta: ResponseMeta
  mission: MissionSummary
}

export interface MissionListResponse {
  meta: ResponseMeta
  missions: MissionListItem[]
}

export interface StageListResponse {
  meta: ResponseMeta
  stages: StageDetail[]
}

export interface HealthApiResponse {
  meta: ResponseMeta
  status: string
  components: Record<string, ComponentHealth>
}

export interface ApprovalListResponse {
  meta: ResponseMeta
  approvals: ApprovalEntry[]
}

export interface TelemetryListResponse {
  meta: ResponseMeta
  events: TelemetryEntry[]
}

export interface CapabilityListResponse {
  meta: ResponseMeta
  capabilities: Record<string, CapabilityEntry>
}

// ── Error ───────────────────────────────────────────────────────

export interface APIError {
  error: string
  detail: string | null
  timestamp: string
}

// ── Create Mission ──────────────────────────────────────────────

export interface CreateMissionRequest {
  goal: string
  complexity?: string
}

export interface CreateMissionResponse {
  meta: ResponseMeta
  missionId: string
  state: string
  goal: string
}

// ── Mutation Response (D-096) ───────────────────────────────────

export interface MutationResponse {
  requestId: string
  lifecycleState: string
  targetId: string
  requestedAt: string
  acceptedAt: string | null
  appliedAt: string | null
  rejectedReason: string | null
  timeoutAt: string | null
}
