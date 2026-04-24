import clsx from "clsx";

import { DocumentStatus } from "@/types/api";

const STATUS_STYLES: Record<DocumentStatus, string> = {
  uploaded: "border-slate-200 bg-slate-50 text-slate-700",
  queued: "border-primary/20 bg-primary-soft text-primary-hover",
  processing: "border-cyan/20 bg-cyan/10 text-cyan",
  extracted: "border-cyan/20 bg-cyan/10 text-cyan",
  chunked: "border-amber/20 bg-amber/10 text-amber",
  indexed: "border-emerald/20 bg-emerald/10 text-emerald",
  failed: "border-rose-200 bg-rose-50 text-rose-700",
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.12em]",
        STATUS_STYLES[status],
      )}
    >
      {status}
    </span>
  );
}
