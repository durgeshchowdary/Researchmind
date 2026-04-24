export function StatCard({
  label,
  value,
  note,
}: {
  label: string;
  value: string | number;
  note: string;
}) {
  return (
    <div className="app-card overflow-hidden p-0">
      <div className="h-1.5 bg-gradient-to-r from-primary via-cyan to-pink-500" />
      <div className="p-4">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-600">{note}</p>
      </div>
    </div>
  );
}
