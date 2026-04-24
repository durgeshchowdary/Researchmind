import { SectionCard } from "@/components/section-card";
import { UploadDropzone } from "@/components/upload-dropzone";


export default function UploadPage() {
  return (
    <SectionCard
      title="Upload documents"
      description="Add PDFs, notes, reports, markdown, or text files."
    >
      <UploadDropzone />
    </SectionCard>
  );
}
