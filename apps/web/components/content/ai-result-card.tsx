"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { AIGenerationResult } from "@/lib/types";

export function AIResultCard({ result }: { result: AIGenerationResult }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(result.result);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <Card className="animate-fade-in">
      <CardContent className="flex flex-col gap-3 p-4">
        <div className="flex items-center justify-between">
          <Badge variant="outline">
            {result.provider} · {result.model}
          </Badge>
          <Button variant="ghost" size="sm" onClick={copy}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{result.result}</p>
      </CardContent>
    </Card>
  );
}
