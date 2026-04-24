import { Suspense } from "react";

import { CompareWorkbench } from "@/components/compare-workbench";


export default function ComparePage() {
  return (
    <section>
      <div className="mb-6">
        <p className="eyebrow">Compare</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
          Find what documents agree on, differ on, and uniquely cover.
        </h1>
        <p className="mt-3 max-w-2xl text-slate-600">
          Compare selected documents with source-backed evidence and clear confidence signals.
        </p>
      </div>
      <Suspense fallback={<div className="app-card p-5 text-sm text-slate-600">Loading comparison workspace...</div>}>
        <CompareWorkbench />
      </Suspense>
    </section>
  );
}
