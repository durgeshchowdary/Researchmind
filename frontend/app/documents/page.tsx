import { DocumentsTable } from "@/components/documents-table";
import { SectionCard } from "@/components/section-card";


export default function DocumentsPage() {
  return (
    <SectionCard
      title="Your documents"
      description="Review uploaded files, indexing status, and available actions."
    >
      <DocumentsTable />
    </SectionCard>
  );
}
