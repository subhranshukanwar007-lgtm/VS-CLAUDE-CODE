"use client";

import { useEffect, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LeadFormDialog } from "@/components/crm/lead-form-dialog";
import { LeadTable } from "@/components/crm/lead-table";
import { PipelineBoard } from "@/components/crm/pipeline-board";
import { api } from "@/lib/api-client";
import type { Lead, PipelineStage } from "@/lib/types";

export default function CrmPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [stages, setStages] = useState<PipelineStage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.get<Lead[]>("/leads"), api.get<PipelineStage[]>("/pipeline-stages")])
      .then(([l, s]) => {
        if (cancelled) return;
        setLeads(l);
        setStages(s);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">CRM</h1>
          <p className="text-sm text-muted-foreground">Leads, prospects, and customers in one pipeline</p>
        </div>
        <LeadFormDialog onCreated={(lead) => setLeads((prev) => [lead, ...prev])} />
      </div>

      {loading ? (
        <Skeleton className="h-96" />
      ) : (
        <Tabs defaultValue="pipeline">
          <TabsList>
            <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
            <TabsTrigger value="leads">All leads</TabsTrigger>
          </TabsList>
          <TabsContent value="pipeline">
            <PipelineBoard stages={stages} leads={leads} onStagesChange={setStages} onLeadsChange={setLeads} />
          </TabsContent>
          <TabsContent value="leads">
            <Card>
              <CardContent className="pt-5">
                <LeadTable leads={leads} onChange={setLeads} />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
