"use client";

import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api-client";
import type { Platform, Post, PostFormat } from "@/lib/types";

const PLATFORMS: Platform[] = ["instagram", "facebook", "youtube", "linkedin", "threads", "pinterest", "tiktok", "x"];
const FORMATS: PostFormat[] = ["reel", "post", "story", "carousel", "video"];

export function PostFormDialog({ onCreated }: { onCreated: (post: Post) => void }) {
  const [open, setOpen] = useState(false);
  const [platform, setPlatform] = useState<Platform>("instagram");
  const [format, setFormat] = useState<PostFormat>("reel");
  const [caption, setCaption] = useState("");
  const [hashtags, setHashtags] = useState("");
  const [mediaUrl, setMediaUrl] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const post = await api.post<Post>("/posts", {
        platform,
        format,
        caption: caption || undefined,
        hashtags: hashtags || undefined,
        media_url: mediaUrl || undefined,
        scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : undefined,
      });
      onCreated(post);
      toast.success(scheduledAt ? "Post scheduled" : "Draft saved");
      setOpen(false);
      setCaption("");
      setHashtags("");
      setMediaUrl("");
      setScheduledAt("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save post");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>New post</Button>
      </DialogTrigger>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Schedule a post</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Platform</Label>
              <Select value={platform} onValueChange={(v) => setPlatform(v as Platform)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PLATFORMS.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Format</Label>
              <Select value={format} onValueChange={(v) => setFormat(v as PostFormat)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FORMATS.map((f) => (
                    <SelectItem key={f} value={f}>
                      {f}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="caption">Caption</Label>
            <Textarea id="caption" value={caption} onChange={(e) => setCaption(e.target.value)} rows={4} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="hashtags">Hashtags</Label>
            <Input id="hashtags" value={hashtags} onChange={(e) => setHashtags(e.target.value)} placeholder="#growth #reels" />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="media">Media URL</Label>
            <Input id="media" value={mediaUrl} onChange={(e) => setMediaUrl(e.target.value)} placeholder="https://..." />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="scheduled">Schedule for (leave blank to save as draft)</Label>
            <Input id="scheduled" type="datetime-local" value={scheduledAt} onChange={(e) => setScheduledAt(e.target.value)} />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving..." : scheduledAt ? "Schedule post" : "Save draft"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
