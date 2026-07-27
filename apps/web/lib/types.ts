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

export interface DashboardOverview {
  summary: DashboardSummary;
  top_posts: TopPost[];
  worst_posts: TopPost[];
  predictions: GrowthPrediction[];
  crm: CrmSummary;
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

export const AGENT_IDS = [
  "ceo",
  "marketing",
  "content",
  "designer",
  "editor",
  "analytics",
  "sales",
  "crm",
  "research",
  "trend",
  "support",
  "scheduler",
] as const;

export type AgentId = (typeof AGENT_IDS)[number];
