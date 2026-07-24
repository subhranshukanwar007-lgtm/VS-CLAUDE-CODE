"use client";

import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { AIResultCard } from "@/components/content/ai-result-card";
import { api, ApiError } from "@/lib/api-client";
import type { AIGenerationResult } from "@/lib/types";

function useGenerator(path: string) {
  const [result, setResult] = useState<AIGenerationResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function generate(body: Record<string, unknown>) {
    setLoading(true);
    setResult(null);
    try {
      const res = await api.post<AIGenerationResult>(path, body);
      setResult(res);
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        toast.error("No AI provider is configured. Set an API key in the backend .env (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY).");
      } else {
        toast.error(err instanceof ApiError ? err.message : "Generation failed");
      }
    } finally {
      setLoading(false);
    }
  }

  return { result, loading, generate };
}

export default function ContentStudioPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI Content Studio</h1>
        <p className="text-sm text-muted-foreground">
          Generate captions, hashtags, and scripts with OpenAI, Claude, or Gemini
        </p>
      </div>

      <Tabs defaultValue="caption">
        <TabsList>
          <TabsTrigger value="caption">Caption</TabsTrigger>
          <TabsTrigger value="hashtags">Hashtags</TabsTrigger>
          <TabsTrigger value="script">Script</TabsTrigger>
        </TabsList>

        <TabsContent value="caption">
          <CaptionGenerator />
        </TabsContent>
        <TabsContent value="hashtags">
          <HashtagGenerator />
        </TabsContent>
        <TabsContent value="script">
          <ScriptGenerator />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ProviderSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="default">Account default</SelectItem>
        <SelectItem value="openai">OpenAI</SelectItem>
        <SelectItem value="anthropic">Claude (Anthropic)</SelectItem>
        <SelectItem value="gemini">Gemini</SelectItem>
      </SelectContent>
    </Select>
  );
}

function CaptionGenerator() {
  const { result, loading, generate } = useGenerator("/ai/caption");
  const [topic, setTopic] = useState("");
  const [platform, setPlatform] = useState("instagram");
  const [tone, setTone] = useState("engaging");
  const [provider, setProvider] = useState("default");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void generate({ topic, platform, tone, provider: provider === "default" ? undefined : provider });
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Caption generator</CardTitle>
          <CardDescription>Describe what the post is about</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label>Topic</Label>
              <Textarea required rows={3} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Launching our new 12-week fitness coaching program" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label>Platform</Label>
                <Input value={platform} onChange={(e) => setPlatform(e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Tone</Label>
                <Input value={tone} onChange={(e) => setTone(e.target.value)} />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>AI provider</Label>
              <ProviderSelect value={provider} onChange={setProvider} />
            </div>
            <Button type="submit" disabled={loading}>
              {loading ? "Generating..." : "Generate caption"}
            </Button>
          </form>
        </CardContent>
      </Card>
      {result && <AIResultCard result={result} />}
    </div>
  );
}

function HashtagGenerator() {
  const { result, loading, generate } = useGenerator("/ai/hashtags");
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(15);
  const [provider, setProvider] = useState("default");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void generate({ topic, count, provider: provider === "default" ? undefined : provider });
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Hashtag generator</CardTitle>
          <CardDescription>Get platform-ready hashtags for a topic</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label>Topic</Label>
              <Textarea required rows={3} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Fitness transformation reels" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>How many hashtags</Label>
              <Input type="number" min={1} max={30} value={count} onChange={(e) => setCount(Number(e.target.value))} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>AI provider</Label>
              <ProviderSelect value={provider} onChange={setProvider} />
            </div>
            <Button type="submit" disabled={loading}>
              {loading ? "Generating..." : "Generate hashtags"}
            </Button>
          </form>
        </CardContent>
      </Card>
      {result && <AIResultCard result={result} />}
    </div>
  );
}

function ScriptGenerator() {
  const { result, loading, generate } = useGenerator("/ai/script");
  const [topic, setTopic] = useState("");
  const [format, setFormat] = useState("reel");
  const [duration, setDuration] = useState(30);
  const [provider, setProvider] = useState("default");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void generate({
      topic,
      format,
      duration_seconds: duration,
      provider: provider === "default" ? undefined : provider,
    });
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Script generator</CardTitle>
          <CardDescription>Hook, body, and CTA for short-form video</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label>Topic</Label>
              <Textarea required rows={3} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="3 mistakes killing your Instagram growth" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label>Format</Label>
                <Input value={format} onChange={(e) => setFormat(e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Duration (seconds)</Label>
                <Input type="number" min={5} max={600} value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>AI provider</Label>
              <ProviderSelect value={provider} onChange={setProvider} />
            </div>
            <Button type="submit" disabled={loading}>
              {loading ? "Generating..." : "Generate script"}
            </Button>
          </form>
        </CardContent>
      </Card>
      {result && <AIResultCard result={result} />}
    </div>
  );
}
