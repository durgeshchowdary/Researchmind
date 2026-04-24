import Link from "next/link";
import { ArrowRight, Files } from "lucide-react";


type FeatureStubProps = {
  title: string;
  description: string;
  nextStep: string;
};

export function FeatureStub({ title, description, nextStep }: FeatureStubProps) {
  return (
    <div className="prose-panel p-6">
      <div className="flex items-start gap-4">
        <div className="rounded-xl bg-primary-soft p-3 text-primary-hover">
          <Files className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Planned page</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">{title}</h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">{description}</p>
          <p className="muted-panel mt-4 text-sm text-slate-700">{nextStep}</p>
          <Link
            href="/documents"
            className="btn-primary mt-5"
          >
            Back to documents
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
