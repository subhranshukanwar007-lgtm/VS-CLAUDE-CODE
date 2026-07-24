"use client";

import { useState, type FormEvent } from "react";
import {
  BarChart3,
  Bot,
  Crown,
  Headset,
  Megaphone,
  Newspaper,
  Palette,
  PenTool,
  Scissors,
  Send,
  TrendingUp,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { AGENT_IDS, type AgentId } from "@/lib/types";

const AGENT_META: Record<AgentId, { label: string; icon: typeof Bot; description: string }> = {
  ceo: { label: "CEO Agent", icon: Crown, description: "Strategy, prioritization, ROI" },
  marketing: { label: "Marketing Agent", icon: Megaphone, description: "Campaigns, positioning, channel mix" },
  content: { label: "Content Agent", icon: PenTool, description: "Ideation, hooks, calendars" },
  designer: { label: "Designer Agent", icon: Palette, description: "Visual direction, thumbnails" },
  editor: { label: "Editor Agent", icon: Scissors, description: "Pacing, cuts, retention" },
  analytics: { label: "Analytics Agent", icon: BarChart3, description: "Performance, grounded in your data" },
  sales: { label: "Sales Agent", icon: TrendingUp, description: "Outreach, objections, closing" },
  crm: { label: "CRM Agent", icon: Users, description: "Pipeline, follow-ups, grounded in your data" },
  research: { label: "Research Agent", icon: Newspaper, description: "Competitor & market research" },
  trend: { label: "Trend Agent", icon: TrendingUp, description: "Trending sounds, hooks, formats" },
  support: { label: "Support Agent", icon: Headset, description: "DM & comment replies" },
  scheduler: { label: "Scheduler Agent", icon: Bot, description: "Cadence, grounded in your data" },
};

interface ChatTurn {
  role: "user" | "agent";
  text: string;
}

export default function AgentsPage() {
  const [active, setActive] = useState<AgentId>("ceo");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<Record<AgentId, ChatTurn[]>>({} as Record<AgentId, ChatTurn[]>);

  const turns = history[active] ?? [];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    const userTurn: ChatTurn = { role: "user", text: message };
    setHistory((prev) => ({ ...prev, [active]: [...(prev[active] ?? []), userTurn] }));
    setMessage("");
    setLoading(true);
    try {
      const res = await api.post<{ result: string }>("/ai/agents/chat", { agent: active, message: userTurn.text });
      setHistory((prev) => ({ ...prev, [active]: [...(prev[active] ?? []), { role: "agent", text: res.result }] }));
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        toast.error("No AI provider is configured. Set an API key in the backend .env.");
      } else {
        toast.error(err instanceof ApiError ? err.message : "Agent request failed");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI Agents</h1>
        <p className="text-sm text-muted-foreground">
          Twelve specialized agents, each an expert system prompt over your configured AI provider — the CRM, Analytics,
          and Scheduler agents ground their answers in your real account data.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-1">
          {AGENT_IDS.map((id) => {
            const meta = AGENT_META[id];
            const Icon = meta.icon;
            return (
              <button
                key={id}
                onClick={() => setActive(id)}
                className={cn(
                  "flex items-center gap-3 rounded-lg border border-border/60 p-3 text-left transition-colors",
                  active === id ? "bg-primary/15 text-primary" : "bg-card/30 hover:bg-secondary/40"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{meta.label}</p>
                  <p className="truncate text-xs text-muted-foreground">{meta.description}</p>
                </div>
              </button>
            );
          })}
        </div>

        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground">
              {AGENT_META[active].label}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-4">
            <div className="flex min-h-64 flex-1 flex-col gap-3 overflow-y-auto rounded-lg border border-border/60 bg-secondary/20 p-4">
              {turns.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  Ask {AGENT_META[active].label} anything within its scope: {AGENT_META[active].description.toLowerCase()}.
                </p>
              )}
              {turns.map((turn, i) => (
                <div
                  key={i}
                  className={cn(
                    "max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap",
                    turn.role === "user" ? "self-end bg-primary text-primary-foreground" : "self-start bg-card"
                  )}
                >
                  {turn.text}
                </div>
              ))}
              {loading && <div className="self-start text-sm text-muted-foreground">Thinking...</div>}
            </div>
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder={`Message ${AGENT_META[active].label}...`}
                disabled={loading}
              />
              <Button type="submit" size="icon" disabled={loading}>
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
