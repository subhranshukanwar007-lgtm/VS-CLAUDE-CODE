"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Eye,
  Flame,
  Globe2,
  Send,
  TrendingUp,
  Users,
  Wallet,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api-client";
import { formatNumber } from "@/lib/utils";
import type { CommandCenter, HotLead, PendingPost } from "@/lib/types";

function relativeTime(iso: string | null): string {
  if (!iso) return "no date set";
  const then = new Date(iso).getTime();
  const diffMinutes = Math.round((then - Date.now()) / 60000);
  const abs = Math.abs(diffMinutes);
  const past = diffMinutes < 0;

  let value: number;
  let unit: string;
  if (abs < 60) {
    value = abs;
    unit = "min";
  } else if (abs < 60 * 24) {
    value = Math.round(abs / 60);
    unit = "hr";
  } else {
    value = Math.round(abs / (60 * 24));
    unit = "day";
  }
  const plural = value === 1 ? "" : "s";
  return past ? `${value} ${unit}${plural} ago` : `in ${value} ${unit}${plural}`;
}

function StatTile({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: typeof Flame;
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <Card className="bg-card/40">
      <CardContent className="flex items-center gap-3 p-4">
        <div className="rounded-lg bg-primary/10 p-2 text-primary">
          <Icon className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-xs text-muted-foreground">{label}</p>
          <p className="text-lg font-semibold leading-tight">{value}</p>
          {hint ? <p className="truncate text-xs text-muted-foreground">{hint}</p> : null}
        </div>
      </CardContent>
    </Card>
  );
}

function HotLeadRow({ lead }: { lead: HotLead }) {
  return (
    <Link
      href={`/crm?lead=${lead.lead_id}`}
      className="flex items-start justify-between gap-3 rounded-lg border border-border/60 bg-card/30 p-3 transition-colors hover:bg-secondary/40"
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="truncate font-medium">{lead.full_name}</span>
          <Badge variant={lead.intent === "hot" ? "destructive" : "secondary"} className="shrink-0">
            {lead.intent === "hot" ? "🔥 hot" : "warm"}
          </Badge>
        </div>
        <p className="truncate text-xs text-muted-foreground">
          {lead.intent_reason ?? "No reason recorded"}
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          from {lead.source}
          {lead.country ? ` · ${lead.country}` : ""} · scored {relativeTime(lead.scored_at)}
        </p>
      </div>
      <Send className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
    </Link>
  );
}

function PendingPostRow({
  post,
  onPublish,
  publishing,
}: {
  post: PendingPost;
  onPublish?: (post: PendingPost) => void;
  publishing?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-border/60 bg-card/30 p-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="shrink-0">
            {post.platform}
          </Badge>
          <span className="text-xs text-muted-foreground">{post.format}</span>
          {post.is_overdue ? (
            <Badge variant="destructive" className="shrink-0">
              overdue
            </Badge>
          ) : null}
          {!post.can_publish ? (
            <Badge variant="secondary" className="shrink-0">
              not connected
            </Badge>
          ) : null}
        </div>
        <p className="mt-1 truncate text-sm">{post.caption ?? "(no caption)"}</p>
        <p className="text-xs text-muted-foreground">{relativeTime(post.scheduled_at)}</p>
      </div>
      {onPublish ? (
        <Button
          size="sm"
          disabled={publishing || !post.can_publish}
          onClick={() => onPublish(post)}
          title={
            post.can_publish
              ? "Approve and publish now"
              : `Publishing to ${post.platform} isn't wired up yet — see Settings`
          }
        >
          {publishing ? "Publishing…" : "Approve"}
        </Button>
      ) : null}
    </div>
  );
}

function Breakdown({
  title,
  icon: Icon,
  rows,
}: {
  title: string;
  icon: typeof Globe2;
  rows: { label: string | null; count: number }[];
}) {
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  return (
    <Card className="bg-card/40">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Icon className="h-4 w-4" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">No leads yet.</p>
        ) : (
          rows.map((row) => {
            const pct = total > 0 ? Math.round((row.count / total) * 100) : 0;
            return (
              <div key={row.label ?? "unknown"} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="capitalize">{row.label ?? "not set"}</span>
                  <span className="text-muted-foreground">
                    {row.count} · {pct}%
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-secondary/50">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}

export default function CommandCenterPage() {
  const [data, setData] = useState<CommandCenter | null>(null);
  const [loading, setLoading] = useState(true);
  const [publishingId, setPublishingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const fresh = await api.get<CommandCenter>("/dashboard/command-center");
    setData(fresh);
  }, []);

  useEffect(() => {
    let cancelled = false;
    api
      .get<CommandCenter>("/dashboard/command-center")
      .then((fresh) => !cancelled && setData(fresh))
      .catch(() => !cancelled && toast.error("Could not load your command center"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  async function handlePublish(post: PendingPost) {
    setPublishingId(post.post_id);
    try {
      await api.post(`/posts/${post.post_id}/publish`);
      toast.success(`Published to ${post.platform}`);
      await load();
    } catch (err) {
      // The backend returns the platform's own error message, which is far more
      // actionable than a generic failure ("Media URL is not reachable" etc).
      toast.error(err instanceof ApiError ? err.message : "Could not publish this post");
    } finally {
      setPublishingId(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!data) {
    return <p className="text-sm text-muted-foreground">Could not load your command center.</p>;
  }

  const needsYou = data.hot_leads.length + data.needs_approval.length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Command Center</h1>
        <p className="text-sm text-muted-foreground">
          {needsYou === 0
            ? "Nothing needs you right now."
            : `${needsYou} thing${needsYou === 1 ? "" : "s"} need you.`}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile icon={Users} label="Followers" value={formatNumber(data.followers)} />
        <StatTile icon={Eye} label="Views (30d)" value={formatNumber(data.views_30d)} />
        <StatTile
          icon={Wallet}
          label="Revenue (30d)"
          value={formatNumber(data.money.revenue_30d)}
          hint={`${data.money.won_deals} won · ${formatNumber(data.money.won_value)}`}
        />
        <StatTile
          icon={TrendingUp}
          label="Open pipeline"
          value={formatNumber(data.money.open_pipeline_value)}
          hint={`${data.money.open_deals} open deal${data.money.open_deals === 1 ? "" : "s"}`}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="bg-card/40">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Flame className="h-4 w-4 text-destructive" />
              Talk to these people
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.hot_leads.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No one has shown buying intent yet. Leads appear here automatically when they ask about price, how to
                join, or availability.
              </p>
            ) : (
              data.hot_leads.map((lead) => <HotLeadRow key={lead.lead_id} lead={lead} />)
            )}
          </CardContent>
        </Card>

        <Card className="bg-card/40">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle2 className="h-4 w-4" />
              Waiting for your approval
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.needs_approval.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No drafts waiting. Posts land here when they&apos;re due and auto-publish is off for that platform.
              </p>
            ) : (
              data.needs_approval.map((post) => (
                <PendingPostRow
                  key={post.post_id}
                  post={post}
                  onPublish={handlePublish}
                  publishing={publishingId === post.post_id}
                />
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="bg-card/40 lg:col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <CalendarClock className="h-4 w-4" />
              Going out next
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.upcoming.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nothing scheduled.</p>
            ) : (
              data.upcoming.map((post) => <PendingPostRow key={post.post_id} post={post} />)
            )}
          </CardContent>
        </Card>

        <Breakdown title="Where leads come from" icon={TrendingUp} rows={data.leads_by_source} />
        <Breakdown title="Which countries" icon={Globe2} rows={data.leads_by_country} />
      </div>

      {Object.values(data.auto_publish).every((enabled) => !enabled) ? (
        <Card className="border-amber-500/40 bg-amber-500/5">
          <CardContent className="flex items-start gap-3 p-4 text-sm">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
            <p className="text-muted-foreground">
              Auto-publish is off for every platform, so scheduled posts will wait here for your approval. Turn it on
              per platform in{" "}
              <Link href="/settings" className="text-primary underline">
                Settings
              </Link>{" "}
              once you trust the output.
            </p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
