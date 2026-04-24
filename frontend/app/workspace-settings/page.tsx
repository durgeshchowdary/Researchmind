"use client";

import { FormEvent, useEffect, useState } from "react";

import { addWorkspaceMember, createWorkspace, fetchWorkspace, fetchWorkspaces } from "@/lib/api";
import { WorkspaceDetail, WorkspaceRole, WorkspaceSummary } from "@/types/api";
import { selectedWorkspaceId } from "@/components/workspace-switcher";


export default function WorkspaceSettingsPage() {
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [detail, setDetail] = useState<WorkspaceDetail | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<WorkspaceRole>("viewer");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const list = await fetchWorkspaces();
    setWorkspaces(list);
    const workspaceId = selectedWorkspaceId() ?? list[0]?.id;
    if (workspaceId) setDetail(await fetchWorkspace(workspaceId));
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Could not load workspaces."));
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    const created = await createWorkspace(name);
    window.localStorage.setItem("researchmind-workspace-id", String(created.id));
    setName("");
    await load();
  }

  async function onAddMember(event: FormEvent) {
    event.preventDefault();
    if (!detail) return;
    setDetail(await addWorkspaceMember(detail.id, email, role));
    setEmail("");
  }

  return (
    <div className="space-y-6">
      <section className="hero-surface rounded-[1.75rem] border border-white/70 p-6 shadow-panel md:p-8">
        <p className="section-eyebrow">Workspace</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-white">Workspace settings</h1>
        <p className="mt-2 text-sm text-slate-300">Manage workspace membership and roles.</p>
      </section>
      {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
      <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="app-card p-5">
          <h2 className="text-lg font-semibold text-slate-950">Workspaces</h2>
          <div className="mt-3 space-y-2">
            {workspaces.map((workspace) => (
              <button key={workspace.id} type="button" onClick={() => fetchWorkspace(workspace.id).then(setDetail)} className="interactive-card w-full p-3 text-left">
                <p className="font-semibold text-slate-950">{workspace.name}</p>
                <p className="text-xs text-slate-500">{workspace.role}</p>
              </button>
            ))}
          </div>
          <form onSubmit={onCreate} className="mt-4 flex gap-2">
            <input className="field" value={name} onChange={(event) => setName(event.target.value)} placeholder="New workspace" />
            <button className="btn-primary" type="submit">Create</button>
          </form>
        </div>
        <div className="app-card p-5">
          <h2 className="text-lg font-semibold text-slate-950">{detail?.name ?? "Select a workspace"}</h2>
          <div className="mt-4 grid gap-2">
            {detail?.members.map((member) => (
              <div key={member.user_id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-3 text-sm">
                <span>{member.email}</span>
                <span className="badge">{member.role}</span>
              </div>
            ))}
          </div>
          {detail?.role === "owner" ? (
            <form onSubmit={onAddMember} className="mt-4 grid gap-2 md:grid-cols-[1fr_auto_auto]">
              <input className="field" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="member@example.com" />
              <select className="field" value={role} onChange={(event) => setRole(event.target.value as WorkspaceRole)}>
                <option value="viewer">viewer</option>
                <option value="editor">editor</option>
                <option value="owner">owner</option>
              </select>
              <button className="btn-primary" type="submit">Add</button>
            </form>
          ) : (
            <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">Owner access is required to manage members.</p>
          )}
        </div>
      </section>
    </div>
  );
}
