"use client";

import { Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api-client";
import { formatDateTime } from "@/lib/utils";
import type { Post, PostStatus } from "@/lib/types";

const STATUS_VARIANT: Record<PostStatus, "secondary" | "default" | "warning" | "success" | "destructive"> = {
  draft: "secondary",
  scheduled: "default",
  publishing: "warning",
  published: "success",
  failed: "destructive",
};

interface ContentCalendarProps {
  posts: Post[];
  onChange: (posts: Post[]) => void;
}

export function ContentCalendar({ posts, onChange }: ContentCalendarProps) {
  async function remove(post: Post) {
    const previous = posts;
    onChange(posts.filter((p) => p.id !== post.id));
    try {
      await api.delete(`/posts/${post.id}`);
    } catch (err) {
      onChange(previous);
      toast.error(err instanceof ApiError ? err.message : "Could not remove post");
    }
  }

  if (posts.length === 0) {
    return <p className="py-12 text-center text-sm text-muted-foreground">No posts yet. Schedule your first one.</p>;
  }

  const sorted = [...posts].sort((a, b) => {
    const aTime = a.scheduled_at ? new Date(a.scheduled_at).getTime() : Infinity;
    const bTime = b.scheduled_at ? new Date(b.scheduled_at).getTime() : Infinity;
    return aTime - bTime;
  });

  return (
    <div className="flex flex-col gap-3">
      {sorted.map((post) => (
        <Card key={post.id}>
          <CardContent className="flex items-start justify-between gap-4 p-4">
            <div className="flex min-w-0 flex-col gap-1">
              <div className="flex items-center gap-2">
                <Badge variant="outline">{post.platform}</Badge>
                <Badge variant="outline">{post.format}</Badge>
                <Badge variant={STATUS_VARIANT[post.status]}>{post.status}</Badge>
              </div>
              <p className="truncate text-sm">{post.caption ?? "(no caption)"}</p>
              {post.hashtags && <p className="truncate text-xs text-muted-foreground">{post.hashtags}</p>}
              <p className="text-xs text-muted-foreground">
                {post.scheduled_at ? `Scheduled for ${formatDateTime(post.scheduled_at)}` : "Not scheduled"}
              </p>
              {post.status === "failed" && post.failure_reason && (
                <p className="text-xs text-destructive">{post.failure_reason}</p>
              )}
            </div>
            <Button variant="ghost" size="icon" onClick={() => remove(post)}>
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
