import { FolderOpen } from "lucide-react";

export default function ProjectsPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-[#94a3b8]">
      <FolderOpen size={48} className="mb-4 opacity-20" />
      <p className="text-sm font-semibold text-[#0f172a]">My Projects</p>
      <p className="text-xs mt-1 text-[#94a3b8]">Full project management coming in Phase 2</p>
    </div>
  );
}
