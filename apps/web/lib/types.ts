export type UserRole = "owner" | "admin" | "member" | "viewer";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  avatar_url: string | null;
  brand_voice: string | null;
  follow_up_days: number;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthResponse {
  tokens: TokenPair;
  user: User;
}

export type LeadSource =
  | "instagram"
  | "facebook"
  | "youtube"
  | "linkedin"
  | "threads"
  | "pinterest"
  | "whatsapp"
  | "website"
  | "referral"
  | "manual"
  | "other";

export type LeadStatus = "lead" | "prospect" | "customer" | "churned";

export type LeadIntent = "unknown" | "cold" | "warm" | "hot";

export interface Lead {
  id: string;
  owner_id: string;
  stage_id: string | null;
  full_name: string;
  email: string | null;
  phone: string | null;
  company: string | null;
  source: LeadSource;
  status: LeadStatus;
  estimated_value: number | null;
  tags: string | null;
  country: string | null;
  intent: LeadIntent;
  intent_reason: string | null;
  intent_scored_at: string | null;
  last_follow_up_at: string | null;
  is_stale: boolean;
}

export interface PipelineStage {
  id: string;
  name: string;
  order: number;
  color: string;
  is_won_stage: boolean;
  is_lost_stage: boolean;
}

export type DealStatus = "open" | "won" | "lost";

export interface Deal {
  id: string;
  lead_id: string;
  stage_id: string | null;
  title: string;
  value: number;
  currency: string;
  status: DealStatus;
}

export type TaskStatus = "todo" | "in_progress" | "done";
export type TaskPriority = "low" | "medium" | "high" | "urgent";

export interface Task {
  id: string;
  assignee_id: string;
  lead_id: string | null;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_at: string | null;
}

export interface Note {
  id: string;
  lead_id: string;
  author_id: string;
  body: string;
  created_at: string;
}

export type Platform =
  | "instagram"
  | "facebook"
  | "youtube"
  | "linkedin"
  | "threads"
  | "pinterest"
  | "tiktok"
  | "x";

export type PostFormat = "reel" | "post" | "story" | "carousel" | "video";
export type PostStatus = "draft" | "scheduled" | "publishing" | "published" | "failed";

export interface SocialAccount {
  id: string;
  platform: Platform;
  handle: string;
  external_account_id: string | null;
  is_active: boolean;
}

export interface Post {
  id: string;
  author_id: string;
  platform: Platform;
  format: PostFormat;
  caption: string | null;
  hashtags: string | null;
  media_url: string | null;
  status: PostStatus;
  scheduled_at: string | null;
  published_at: string | null;
  failure_reason: string | null;
  external_post_id: string | null;
}

export type NotificationType =
  | "task_due"
  | "post_published"
  | "post_failed"
  | "lead_created"
  | "deal_won"
  | "system";

export interface AppNotification {
  id: string;
  type: NotificationType;
  title: string;
  body: string | null;
  is_read: boolean;
  link: string | null;
  created_at: string;
}

export interface MetricPoint {
  date: string;
  value: number;
}

export interface DashboardSummary {
  followers: number;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  revenue: number;
  conversions: number;
  watch_time_seconds: number;
  ctr: number;
  retention: number;
  followers_series: MetricPoint[];
  views_series: MetricPoint[];
  revenue_series: MetricPoint[];
}

export interface TopPost {
  post_id: string;
  platform: Platform;
  caption: string | null;
  score: number;
}

export interface GrowthPrediction {
  metric: string;
  method: string;
  projected_30d: number;
  confidence: number;
}

export interface CrmSummary {
  total_leads: number;
  open_deals: number;
  won_deals: number;
  pipeline_value: number;
  won_value: number;
}

export interface LeadBreakdown {
  label: string | null;
  count: number;
}

export interface DashboardOverview {
  summary: DashboardSummary;
  top_posts: TopPost[];
  worst_posts: TopPost[];
  predictions: GrowthPrediction[];
  crm: CrmSummary;
  leads_by_source: LeadBreakdown[];
  leads_by_country: LeadBreakdown[];
}

export interface HotLead {
  lead_id: string;
  full_name: string;
  source: string;
  country: string | null;
  intent: LeadIntent;
  intent_reason: string | null;
  scored_at: string | null;
}

export interface PendingPost {
  post_id: string;
  platform: Platform;
  format: PostFormat;
  caption: string | null;
  status: PostStatus;
  scheduled_at: string | null;
  is_overdue: boolean;
  can_publish: boolean;
}

export interface MoneySnapshot {
  revenue_30d: number;
  won_deals: number;
  won_value: number;
  open_deals: number;
  open_pipeline_value: number;
}

export interface CommandCenter {
  hot_leads: HotLead[];
  needs_approval: PendingPost[];
  upcoming: PendingPost[];
  money: MoneySnapshot;
  followers: number;
  views_30d: number;
  unread_notifications: number;
  leads_by_source: LeadBreakdown[];
  leads_by_country: LeadBreakdown[];
  auto_publish: Record<string, boolean>;
}

export interface AutomationSetting {
  id: string;
  owner_id: string;
  auto_publish: Record<string, boolean>;
  dm_enabled: boolean;
  dm_trigger_keywords: string | null;
  dm_template: string;
  dm_link: string | null;
  threads_monitor_enabled: boolean;
  threads_keywords: string | null;
  threads_max_per_day: number;
  posts_per_day: number;
  reply_language: "english" | "hinglish" | "hindi";
}

export interface PlatformCapability {
  platform: Platform;
  can_publish: boolean;
  supports_stories: boolean;
  note: string | null;
}

export type AIProviderKind = "openai" | "anthropic" | "gemini";

export interface AIGenerationResult {
  id: string;
  provider: AIProviderKind;
  model: string;
  result: string;
}

export interface FollowUpResult {
  generation: AIGenerationResult;
  task: Task;
}

export type VideoProviderKind = "replicate" | "higgsfield";
export type VideoGenerationStatus = "pending" | "processing" | "succeeded" | "failed";

export interface VideoGeneration {
  id: string;
  provider: VideoProviderKind;
  model: string;
  prompt: string;
  status: VideoGenerationStatus;
  video_url: string | null;
  thumbnail_url: string | null;
  error: string | null;
  post_id: string | null;
  created_at: string;
}

// Must stay in sync with AGENT_PERSONAS in apps/api/app/services/agents/personas.py.
export const AGENT_IDS = ["content", "crm", "sales", "analytics", "money", "support"] as const;

// Agents whose answers are grounded in real account data pulled from Postgres
// (DATA_GROUNDED_AGENTS on the backend).
export const GROUNDED_AGENT_IDS: readonly AgentId[] = ["crm", "sales", "analytics", "money"];

export type AgentId = (typeof AGENT_IDS)[number];
