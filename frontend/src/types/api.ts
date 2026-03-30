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

// ── Tool Call Detail ────────────────────────────────────────────

export interface ToolCallDetail {
  tool: string
  params: Record<string, unknown>
  success: boolean
  error: string | null
  durationMs: number
  risk: string
  tokenTruncated: boolean
  tokenBlocked: boolean
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
  toolCallDetails: ToolCallDetail[]
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
  reason: string | null
  requestedByRole: string | null
  expiresAt: string | null
  decidedBy: string | null
  stageId: string | null
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

// ── Roles ──────────────────────────────────────────────────────

export interface RoleInfo {
  name: string
  defaultSkill: string
  allowedSkills: string[]
  toolPolicy: string
  model: string
  tools: string[]
  discoveryRights: string
  maxFileReads: number
  promptPreview: string
}

export interface RolesResponse {
  meta: ResponseMeta
  roles: Record<string, RoleInfo>
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

// ── Token Report (D-102) ─────────────────────────────────────────

export interface TokenStageReport {
  stage: string
  tokens_consumed: number
  tool_calls: number
  pct_of_total: number
}

export interface TokenReport {
  mission_id: string
  status: string
  generated_at: string
  total_tokens: number
  total_tool_calls: number
  truncations: number
  blocks: number
  stages: TokenStageReport[]
}

// ── Template (B-104) ───────────────────────────────────────────

export interface TemplateParameter {
  name: string
  type: 'string' | 'number' | 'boolean' | 'array'
  required: boolean
  description: string
  default?: string | number | boolean | string[]
}

export interface MissionConfig {
  goal_template: string
  specialist: string
  provider: string
  max_stages: number
  timeout_minutes: number
}

export interface MissionTemplate {
  id: string
  name: string
  description: string
  version: string
  author: string
  status: 'draft' | 'published' | 'archived'
  parameters: TemplateParameter[]
  mission_config: MissionConfig
  created_at: string
  updated_at: string
}

// ── Cost Dashboard (B-105) ─────────────────────────────────────

export interface ProviderBreakdown {
  tokens: number
  missions: number
  estimated_cost: number
}

export interface CostSummary {
  meta: ResponseMeta
  total_missions: number
  completed: number
  failed: number
  success_rate: number
  total_tokens: number
  total_estimated_cost: number
  avg_cost_per_mission: number
  avg_tokens_per_completed: number
  avg_duration_ms: number
  total_tool_calls: number
  total_reworks: number
  total_budget_events: number
  provider_breakdown: Record<string, ProviderBreakdown>
  pricing_model: Record<string, { input: number; output: number }>
}

export interface CostMission {
  id: string
  goal: string
  status: string
  complexity: string
  tokens: number
  estimated_cost: number
  provider: string
  duration_ms: number
  stages: number
  tool_calls: number
  reworks: number
  budget_pct: number
  ts: string
}

export interface CostMissionsResponse {
  meta: ResponseMeta
  total: number
  missions: CostMission[]
}

export interface TrendBucket {
  period: string
  tokens: number
  estimated_cost: number
  missions: number
  completed: number
  failed: number
  success_rate: number
}

export interface CostTrendsResponse {
  meta: ResponseMeta
  bucket: string
  trends: TrendBucket[]
}

// ── Agent Health (B-108) ───────────────────────────────────────

export interface ProviderStatus {
  name: string
  provider: string
  model: string
  status: string
  detail: string
}

export interface ProvidersResponse {
  meta: ResponseMeta
  status: string
  providers: ProviderStatus[]
  available_count: number
  total_count: number
}

export interface AgentRole {
  id: string
  displayName: string
  defaultSkill: string
  allowedSkills: string[]
  forbiddenSkills: string[]
  toolPolicy: string
  allowedTools: string[]
  toolCount: number
  defaultModelTier: number
  preferredModel: string
  discoveryRights: string
  maxFileReads: number
  maxDirectoryReads: number
  canExpand: boolean
}

export interface AgentRolesResponse {
  meta: ResponseMeta
  total: number
  roles: AgentRole[]
}

export interface CapabilityMatrixEntry {
  role: string
  displayName: string
  preferredModel: string
  modelTier: number
  toolPolicy: string
  toolCount: number
  canExpand: boolean
  discoveryRights: string
}

export interface CapabilityMatrixResponse {
  meta: ResponseMeta
  matrix: CapabilityMatrixEntry[]
}

export interface RolePerformance {
  role: string
  missions: number
  stages: number
  tool_calls: number
  reworks: number
  avg_stage_duration_ms: number
  rework_rate: number
}

export interface AgentPerformanceResponse {
  meta: ResponseMeta
  performance: RolePerformance[]
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
