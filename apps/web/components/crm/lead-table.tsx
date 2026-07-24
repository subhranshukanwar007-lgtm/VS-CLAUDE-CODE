"use client";

import { Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api-client";
import { formatCurrency } from "@/lib/utils";
import type { Lead, LeadStatus } from "@/lib/types";

const STATUSES: LeadStatus[] = ["lead", "prospect", "customer", "churned"];

const STATUS_VARIANT: Record<LeadStatus, "default" | "secondary" | "success" | "destructive"> = {
  lead: "secondary",
  prospect: "default",
  customer: "success",
  churned: "destructive",
};

interface LeadTableProps {
  leads: Lead[];
  onChange: (leads: Lead[]) => void;
}

export function LeadTable({ leads, onChange }: LeadTableProps) {
  async function updateStatus(lead: Lead, status: LeadStatus) {
    const previous = leads;
    onChange(leads.map((l) => (l.id === lead.id ? { ...l, status } : l)));
    try {
      await api.patch<Lead>(`/leads/${lead.id}`, { status });
    } catch (err) {
      onChange(previous);
      toast.error(err instanceof ApiError ? err.message : "Could not update lead");
    }
  }

  async function remove(lead: Lead) {
    const previous = leads;
    onChange(leads.filter((l) => l.id !== lead.id));
    try {
      await api.delete(`/leads/${lead.id}`);
      toast.success("Lead removed");
    } catch (err) {
      onChange(previous);
      toast.error(err instanceof ApiError ? err.message : "Could not remove lead");
    }
  }

  if (leads.length === 0) {
    return <p className="py-10 text-center text-sm text-muted-foreground">No leads yet — add your first one.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Company</TableHead>
          <TableHead>Source</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Est. value</TableHead>
          <TableHead className="w-10" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {leads.map((lead) => (
          <TableRow key={lead.id}>
            <TableCell>
              <div className="flex flex-col">
                <span className="font-medium">{lead.full_name}</span>
                {lead.email && <span className="text-xs text-muted-foreground">{lead.email}</span>}
              </div>
            </TableCell>
            <TableCell>{lead.company ?? "—"}</TableCell>
            <TableCell>
              <Badge variant="outline">{lead.source}</Badge>
            </TableCell>
            <TableCell>
              <Select value={lead.status} onValueChange={(v) => updateStatus(lead, v as LeadStatus)}>
                <SelectTrigger className="h-7 w-32">
                  <SelectValue>
                    <Badge variant={STATUS_VARIANT[lead.status]}>{lead.status}</Badge>
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {STATUSES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </TableCell>
            <TableCell>{lead.estimated_value ? formatCurrency(lead.estimated_value) : "—"}</TableCell>
            <TableCell>
              <Button variant="ghost" size="icon" onClick={() => remove(lead)}>
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
