"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Image as ImageIcon, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { AttachToPostDialog } from "@/components/video/attach-to-post-dialog";
import { api, ApiError } from "@/lib/api-client";
import { formatDateTime } from "@/lib/utils";
import type { VideoGeneration, VideoGenerationStatus, VideoProviderKind } from "@/lib/types";

const POLL_INTERVAL_MS = 4000;
const IN_FLIGHT: VideoGenerationStatus[] = ["pending", "processing"];

const STATUS_VARIANT: Record<VideoGenerationStatus, "secondary" | "warning" | "success" | "destructive"> = {
  pending: "secondary",
  processing: "warning",
  succeeded: "success",
  failed: "destructive",
};

const PROVIDER_LABEL: Record<VideoProviderKind, string> = {
  replicate: "Replicate",
  higgsfield: "Higgsfield",
};

const PROVIDER_HINT: Record<VideoProviderKind, string> = {
  replicate: "owner/name slug — browse options at replicate.com/collections/text-to-video",
  higgsfield: "Higgsfield model_id, e.g. higgsfield-ai/soul/standard — check your Higgsfield dashboard",
};

export default function VideoStudioPage() {
  const [generations, setGenerations] = useState<VideoGeneration[]>([]);
  const [loading, setLoading] = useState(true);
  const [provider, setProvider] = useState<VideoProviderKind>("replicate");
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [thumbnailingId, setThumbnailingId] = useState<string | null>(null);
  const generationsRef = useRef(generations);

  useEffect(() => {
    generationsRef.current = generations;
  }, [generations]);

  useEffect(() => {
    let cancelled = false;
    api
      .get<VideoGeneration[]>("/video")
      .then((data) => !cancelled && setGenerations(data))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const interval = setInterval(async () => {
      const inFlight = generationsRef.current.filter((g) => IN_FLIGHT.includes(g.status));
      if (inFlight.length === 0) return;
      const updates = await Promise.all(
        inFlight.map((g) => api.get<VideoGeneration>(`/video/${g.id}`).catch(() => g))
      );
      setGenerations((prev) => prev.map((g) => updates.find((u) => u.id === g.id) ?? g));
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const generation = await api.post<VideoGeneration>("/video/generate", {
        prompt,
        provider,
        model: model || undefined,
        extra_params: imageUrl ? { image: imageUrl } : undefined,
      });
      setGenerations((prev) => [generation, ...prev]);
      setPrompt("");
      setImageUrl("");
      toast.success("Video generation started");
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        toast.error(
          provider === "higgsfield"
            ? "Higgsfield isn't configured. Set HIGGSFIELD_API_KEY and HIGGSFIELD_API_SECRET in the backend .env."
            : "No video provider is configured. Set REPLICATE_API_TOKEN in the backend .env."
        );
      } else {
        toast.error(err instanceof ApiError ? err.message : "Could not start generation");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function generateThumbnail(generation: VideoGeneration) {
    setThumbnailingId(generation.id);
    try {
      const updated = await api.post<VideoGeneration>(`/video/${generation.id}/thumbnail`);
      setGenerations((prev) => prev.map((g) => (g.id === generation.id ? updated : g)));
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        toast.error("Thumbnail generation needs REPLICATE_API_TOKEN set in the backend .env.");
      } else {
        toast.error(err instanceof ApiError ? err.message : "Could not generate thumbnail");
      }
    } finally {
      setThumbnailingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI Video Studio</h1>
        <p className="text-sm text-muted-foreground">
          Generate a video from a prompt (or an image, for image-to-video), then send it straight to the content
          calendar as a draft post.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Generate a video</CardTitle>
            <CardDescription>Choose Replicate (broad model catalog) or Higgsfield (avatar/persona models)</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label>Provider</Label>
                <Select value={provider} onValueChange={(v) => setProvider(v as VideoProviderKind)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="replicate">{PROVIDER_LABEL.replicate}</SelectItem>
                    <SelectItem value="higgsfield">{PROVIDER_LABEL.higgsfield}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="prompt">Prompt</Label>
                <Textarea
                  id="prompt"
                  required
                  rows={4}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="A golden retriever surfing a small wave at sunset, cinematic, slow motion"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="model">Model (optional)</Label>
                <Input
                  id="model"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder={`Defaults to the backend's configured ${PROVIDER_LABEL[provider]} model`}
                />
                <p className="text-xs text-muted-foreground">{PROVIDER_HINT[provider]}</p>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="imageUrl">Source image URL (optional, for image-to-video)</Label>
                <Input
                  id="imageUrl"
                  value={imageUrl}
                  onChange={(e) => setImageUrl(e.target.value)}
                  placeholder="https://..."
                />
                {provider === "higgsfield" && (
                  <p className="text-xs text-muted-foreground">
                    For avatar/voice inputs specific to your Higgsfield account (reference face, voice ID), use the
                    API directly with an `extra_params` body until your exact field names are confirmed against your
                    dashboard.
                  </p>
                )}
              </div>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Starting..." : "Generate video"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4">
          {loading && <Skeleton className="h-48" />}
          {!loading && generations.length === 0 && (
            <Card>
              <CardContent className="py-12 text-center text-sm text-muted-foreground">
                No videos generated yet — try a prompt on the left.
              </CardContent>
            </Card>
          )}
          {generations.map((generation) => (
            <Card key={generation.id} className="animate-fade-in">
              <CardContent className="flex flex-col gap-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm">{generation.prompt}</p>
                  <Badge variant={STATUS_VARIANT[generation.status]} className="shrink-0">
                    {IN_FLIGHT.includes(generation.status) && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                    {generation.status}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline">{PROVIDER_LABEL[generation.provider]}</Badge>
                  <span>{generation.model}</span>
                  <span>·</span>
                  <span>{formatDateTime(generation.created_at)}</span>
                </div>

                {generation.status === "succeeded" && generation.video_url && (
                  <>
                    <video src={generation.video_url} controls className="w-full max-w-md rounded-lg border border-border/60" />

                    {generation.thumbnail_url && (
                      <img
                        src={generation.thumbnail_url}
                        alt="Generated thumbnail"
                        className="h-24 w-24 rounded-lg border border-border/60 object-cover"
                      />
                    )}

                    <div className="flex flex-wrap items-center gap-2">
                      {generation.post_id ? (
                        <Badge variant="outline">Added to content calendar</Badge>
                      ) : (
                        <AttachToPostDialog
                          generation={generation}
                          onAttached={() =>
                            setGenerations((prev) =>
                              prev.map((g) => (g.id === generation.id ? { ...g, post_id: "pending" } : g))
                            )
                          }
                        />
                      )}
                      {!generation.thumbnail_url && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={thumbnailingId === generation.id}
                          onClick={() => generateThumbnail(generation)}
                        >
                          <ImageIcon className="h-4 w-4" />
                          {thumbnailingId === generation.id ? "Generating thumbnail..." : "Generate thumbnail"}
                        </Button>
                      )}
                    </div>
                  </>
                )}

                {generation.status === "failed" && generation.error && (
                  <p className="text-xs text-destructive">{generation.error}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
