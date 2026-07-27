"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api-client";
import type { Platform, SocialAccount } from "@/lib/types";

const PLATFORMS: Platform[] = ["instagram", "facebook", "youtube", "linkedin", "threads", "pinterest", "tiktok", "x"];

export function ConnectedAccounts() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [platform, setPlatform] = useState<Platform>("instagram");
  const [handle, setHandle] = useState("");
  const [externalId, setExternalId] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .get<SocialAccount[]>("/social-accounts")
      .then((data) => !cancelled && setAccounts(data))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const account = await api.post<SocialAccount>("/social-accounts", {
        platform,
        handle,
        external_account_id: externalId || undefined,
      });
      setAccounts((prev) => [...prev, account]);
      setHandle("");
      setExternalId("");
      toast.success("Account connected");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not connect account");
    } finally {
      setSubmitting(false);
    }
  }

  async function remove(account: SocialAccount) {
    const previous = accounts;
    setAccounts((prev) => prev.filter((a) => a.id !== account.id));
    try {
      await api.delete(`/social-accounts/${account.id}`);
    } catch (err) {
      setAccounts(previous);
      toast.error(err instanceof ApiError ? err.message : "Could not remove account");
    }
  }

  if (loading) return <Skeleton className="h-32" />;

  return (
    <div className="flex flex-col gap-4">
      {accounts.length > 0 && (
        <div className="flex flex-col gap-2">
          {accounts.map((account) => (
            <div
              key={account.id}
              className="flex items-center justify-between gap-2 rounded-md border border-border/60 px-3 py-2"
            >
              <div className="flex items-center gap-2 text-sm">
                <Badge variant="outline">{account.platform}</Badge>
                <span>{account.handle}</span>
                {account.external_account_id && (
                  <span className="text-xs text-muted-foreground">ID: {account.external_account_id}</span>
                )}
              </div>
              <Button variant="ghost" size="icon" onClick={() => remove(account)}>
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-md border border-border/60 p-3">
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
            <Label htmlFor="handle">Handle</Label>
            <Input id="handle" required value={handle} onChange={(e) => setHandle(e.target.value)} placeholder="@yourhandle" />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="externalId">Business account ID (optional)</Label>
          <Input
            id="externalId"
            value={externalId}
            onChange={(e) => setExternalId(e.target.value)}
            placeholder="From your Meta Business Suite / API dashboard"
          />
          <p className="text-xs text-muted-foreground">
            Required only for automatic comment-to-lead capture — this is how an incoming webhook event gets
            routed to your account. Not needed for posting/scheduling.
          </p>
        </div>
        <Button type="submit" disabled={submitting} className="w-fit">
          {submitting ? "Connecting..." : "Connect account"}
        </Button>
      </form>
    </div>
  );
}
