import { SearchWorkbench } from "@/components/search-workbench";
import { SectionCard } from "@/components/section-card";


export default function SearchPage() {
  return (
    <SectionCard
      title="Search your knowledge base"
      description="Search uploaded documents and inspect why each result appears."
    >
      <SearchWorkbench />
    </SectionCard>
  );
}
