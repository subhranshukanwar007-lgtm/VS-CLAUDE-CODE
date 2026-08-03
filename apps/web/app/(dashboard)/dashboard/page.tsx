"use client";

import { useEffect, useState } from "react";
import {
  DollarSign,
  Eye,
  Heart,
  MessageCircle,
  Share2,
  TrendingUp,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/dashboard/stat-card";
import { MetricChart } from "@/components/dashboard/metric-chart";
import { api } from "@/lib/api-client";
import { formatCurrency, formatNumber } from "@/lib/utils";
import type { DashboardOverview } from "@/lib/types";

export default function DashboardPage() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get<DashboardOverview>("/dashboard/overview")
      .then((data) => !cancelled && setOverview(data))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    );
  }

  if (!overview) return null;

  const { summary, top_posts, worst_posts, predictions, crm } = overview;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Last 30 days across all connected platforms</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Followers" value={formatNumber(summary.followers)} icon={Users} accent="primary" />
        <StatCard label="Views" value={formatNumber(summary.views)} icon={Eye} accent="accent" />
        <StatCard label="Likes" value={formatNumber(summary.likes)} icon={Heart} accent="warning" />
        <StatCard label="Comments" value={formatNumber(summary.comments)} icon={MessageCircle} accent="primary" />
        <StatCard label="Shares" value={formatNumber(summary.shares)} icon={Share2} accent="accent" />
        <StatCard label="Revenue" value={formatCurrency(summary.revenue)} icon={DollarSign} accent="success" />
        <StatCard label="Conversions" value={formatNumber(summary.conversions)} icon={TrendingUp} accent="success" />
        <StatCard label="Avg CTR" value={`${summary.ctr.toFixed(2)}%`} icon={TrendingUp} accent="warning" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <MetricChart title="Followers" data={summary.followers_series} color="#a78bfa" gradientId="followers" />
        <MetricChart title="Views" data={summary.views_series} color="#22d3ee" gradientId="views" />
        <MetricChart title="Revenue" data={summary.revenue_series} color="#34d399" gradientId="revenue" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Top posts</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 pt-0">
            {top_posts.length === 0 && <EmptyPosts />}
            {top_posts.map((p) => (
              <div key={p.post_id} className="flex items-center justify-between gap-2 rounded-md border border-border/60 px-3 py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm">{p.caption ?? "(no caption)"}</p>
                  <Badge variant="outline" className="mt-1">{p.platform}</Badge>
                </div>
                <span className="text-sm font-semibold text-success">{formatNumber(p.score)}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Needs attention</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 pt-0">
            {worst_posts.length === 0 && <EmptyPosts />}
            {worst_posts.map((p) => (
              <div key={p.post_id} className="flex items-center justify-between gap-2 rounded-md border border-border/60 px-3 py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm">{p.caption ?? "(no caption)"}</p>
                  <Badge variant="outline" className="mt-1">{p.platform}</Badge>
                </div>
                <span className="text-sm font-semibold text-destructive">{formatNumber(p.score)}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>30-day growth projection</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 pt-0">
            {predictions.map((p) => (
              <div key={p.metric} className="flex items-center justify-between">
                <div>
                  <p className="text-sm capitalize">{p.metric}</p>
                  <p className="text-[11px] text-muted-foreground">confidence {Math.round(p.confidence * 100)}%</p>
                </div>
                <span className="text-sm font-semibold">{formatNumber(p.projected_30d)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>CRM snapshot</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 pt-0 sm:grid-cols-5">
          <Snapshot label="Total leads" value={crm.total_leads} />
          <Snapshot label="Open deals" value={crm.open_deals} />
          <Snapshot label="Won deals" value={crm.won_deals} />
          <Snapshot label="Pipeline value" value={formatCurrency(crm.pipeline_value)} />
          <Snapshot label="Won value" value={formatCurrency(crm.won_value)} />
        </CardContent>
      </Card>
    </div>
  );
}

function Snapshot({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-lg font-semibold">{value}</span>
    </div>
  );
}

function EmptyPosts() {
  return <p className="py-6 text-center text-sm text-muted-foreground">No post metrics yet</p>;
}
