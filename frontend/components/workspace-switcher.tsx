"use client";

import { useEffect, useState } from "react";

import { fetchWorkspaces } from "@/lib/api";
import { WorkspaceSummary } from "@/types/api";


export function selectedWorkspaceId(): number | undefined {
  if (typeof window === "undefined") return undefined;
  const value = window.localStorage.getItem("researchmind-workspace-id");
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

export function WorkspaceSwitcher() {
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [selected, setSelected] = useState<number | "">("");

  useEffect(() => {
    fetchWorkspaces()
      .then((items) => {
        setWorkspaces(items);
        const existing = selectedWorkspaceId();
        const next = existing && items.some((workspace) => workspace.id === existing) ? existing : items[0]?.id;
        if (next) {
          setSelected(next);
          window.localStorage.setItem("researchmind-workspace-id", String(next));
        }
      })
      .catch(() => setWorkspaces([]));
  }, []);

  if (!workspaces.length) {
    return null;
  }

  return (
    <select
      aria-label="Workspace"
      className="hidden rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm md:block"
      value={selected}
      onChange={(event) => {
        const workspaceId = Number(event.target.value);
        setSelected(workspaceId);
        window.localStorage.setItem("researchmind-workspace-id", String(workspaceId));
        window.dispatchEvent(new Event("researchmind-workspace-change"));
      }}
    >
      {workspaces.map((workspace) => (
        <option key={workspace.id} value={workspace.id}>
          {workspace.name} ({workspace.role})
        </option>
      ))}
    </select>
  );
}
