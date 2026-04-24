import { SectionCard } from "@/components/section-card";
import { AskWorkbench } from "@/components/ask-workbench";


export default function AskPage() {
  return (
    <SectionCard
      title="Ask your documents"
      description="Ask a question and see the source text behind the answer."
    >
      <AskWorkbench />
    </SectionCard>
  );
}
