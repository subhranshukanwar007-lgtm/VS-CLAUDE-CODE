"use client";

import { useEffect, useState } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { ContentCalendar } from "@/components/calendar/content-calendar";
import { PostFormDialog } from "@/components/calendar/post-form-dialog";
import { api } from "@/lib/api-client";
import type { Post } from "@/lib/types";

export default function CalendarPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get<Post[]>("/posts")
      .then((data) => !cancelled && setPosts(data))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Content calendar</h1>
          <p className="text-sm text-muted-foreground">Plan, schedule, and track posts across every platform</p>
        </div>
        <PostFormDialog onCreated={(post) => setPosts((prev) => [post, ...prev])} />
      </div>

      {loading ? <Skeleton className="h-96" /> : <ContentCalendar posts={posts} onChange={setPosts} />}
    </div>
  );
}
