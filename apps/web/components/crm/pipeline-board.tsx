"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api-client";
import { formatCurrency } from "@/lib/utils";
import type { Lead, PipelineStage } from "@/lib/types";

const DEFAULT_STAGES: Array<{ name: string; order: number; color: string }> = [
  { name: "New", order: 0, color: "#6366f1" },
  { name: "Contacted", order: 1, color: "#8b5cf6" },
  { name: "Qualified", order: 2, color: "#06b6d4" },
  { name: "Won", order: 3, color: "#22c55e" },
  { name: "Lost", order: 4, color: "#ef4444" },
];

interface PipelineBoardProps {
  stages: PipelineStage[];
  leads: Lead[];
  onStagesChange: (stages: PipelineStage[]) => void;
  onLeadsChange: (leads: Lead[]) => void;
}

export function PipelineBoard({ stages, leads, onStagesChange, onLeadsChange }: PipelineBoardProps) {
  const [seeding, setSeeding] = useState(false);

  async function seedDefaultStages() {
    setSeeding(true);
    try {
      const created: PipelineStage[] = [];
      for (const stage of DEFAULT_STAGES) {
        created.push(await api.post<PipelineStage>("/pipeline-stages", stage));
      }
      onStagesChange(created);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not create pipeline stages");
    } finally {
      setSeeding(false);
    }
  }

  async function moveLead(leadId: string, stageId: string) {
    const previous = leads;
    onLeadsChange(leads.map((l) => (l.id === leadId ? { ...l, stage_id: stageId } : l)));
    try {
      await api.patch<Lead>(`/leads/${leadId}`, { stage_id: stageId });
    } catch (err) {
      onLeadsChange(previous);
      toast.error(err instanceof ApiError ? err.message : "Could not move lead");
    }
  }

  if (stages.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-12">
          <p className="text-sm text-muted-foreground">No pipeline stages yet.</p>
          <Button onClick={seedDefaultStages} disabled={seeding}>
            {seeding ? "Creating..." : "Create default pipeline"}
          </Button>
        </CardContent>
      </Card>
    );
  }

  const sortedStages = [...stages].sort((a, b) => a.order - b.order);

  return (
    <div className="flex gap-4 overflow-x-auto pb-2">
      {sortedStages.map((stage) => {
        const stageLeads = leads.filter((l) => l.stage_id === stage.id);
        const stageValue = stageLeads.reduce((sum, l) => sum + (l.estimated_value ?? 0), 0);

        return (
          <div
            key={stage.id}
            className="flex w-72 shrink-0 flex-col gap-3 rounded-xl border border-border/60 bg-card/30 p-3"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              const leadId = e.dataTransfer.getData("text/lead-id");
              if (leadId) void moveLead(leadId, stage.id);
            }}
          >
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ background: stage.color }} />
                <span className="text-sm font-semibold">{stage.name}</span>
                <Badge variant="secondary">{stageLeads.length}</Badge>
              </div>
            </div>
            <span className="px-1 text-xs text-muted-foreground">{formatCurrency(stageValue)}</span>

            <div className="flex flex-col gap-2">
              {stageLeads.map((lead) => (
                <Card
                  key={lead.id}
                  draggable
                  onDragStart={(e) => e.dataTransfer.setData("text/lead-id", lead.id)}
                  className="cursor-grab active:cursor-grabbing"
                >
                  <CardHeader className="p-3 pb-1">
                    <CardTitle className="flex items-center gap-1.5 text-sm font-medium text-foreground">
                      {lead.full_name}
                      {lead.is_stale && (
                        <span
                          title="Needs follow-up"
                          className="h-1.5 w-1.5 shrink-0 rounded-full bg-warning"
                        />
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex items-center justify-between p-3 pt-0">
                    <Badge variant="outline">{lead.source}</Badge>
                    {lead.estimated_value ? (
                      <span className="text-xs font-medium">{formatCurrency(lead.estimated_value)}</span>
                    ) : null}
                  </CardContent>
                </Card>
              ))}
              {stageLeads.length === 0 && (
                <p className="rounded-md border border-dashed border-border/60 py-6 text-center text-xs text-muted-foreground">
                  Drop leads here
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
