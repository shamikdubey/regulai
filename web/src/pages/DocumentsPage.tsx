import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload, FileText, CheckCircle, Clock, AlertCircle,
  Loader2, X, ChevronDown,
} from "lucide-react";
import toast from "react-hot-toast";
import { api, Document } from "@/lib/api";
import { cn, formatBytes, JURISDICTIONS, DOMAINS } from "@/lib/utils";

export default function DocumentsPage() {
  const qc = useQueryClient();
  const [uploadJurisdiction, setUploadJurisdiction] = useState("");
  const [uploadDomain, setUploadDomain] = useState("");
  const [uploading, setUploading] = useState<string[]>([]);

  const docsQ = useQuery({
    queryKey: ["documents"],
    queryFn: api.getDocuments,
    refetchInterval: (query) => {
      const hasPending = query.state.data?.some((d) => d.processing_status === "pending");
      return hasPending ? 3000 : false;
    },
  });

  const uploadMut = useMutation({
    mutationFn: ({ file, j, d }: { file: File; j: string; d: string }) =>
      api.uploadDocument(file, j || undefined, d || undefined),
    onSuccess: () => {
      toast.success("Document uploaded — processing in background");
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: () => toast.error("Upload failed"),
  });

  const onDrop = useCallback(
    async (accepted: File[]) => {
      for (const file of accepted) {
        setUploading((p) => [...p, file.name]);
        try {
          await uploadMut.mutateAsync({ file, j: uploadJurisdiction, d: uploadDomain });
        } finally {
          setUploading((p) => p.filter((n) => n !== file.name));
        }
      }
    },
    [uploadJurisdiction, uploadDomain, uploadMut]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    maxSize: 50 * 1024 * 1024,
  });

  const docs = docsQ.data || [];
  const pending = docs.filter((d) => d.processing_status === "pending").length;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="font-serif text-2xl text-[#e8ecf2] mb-1">Documents</h1>
        <p className="text-sm text-[#4a5568]">
          Upload regulatory PDFs or DOCX files. They are parsed, chunked, embedded, and added to your
          private search corpus so the AI can reference them in queries.
        </p>
      </div>

      {/* Upload zone */}
      <div className="mb-8">
        {/* Metadata selectors */}
        <div className="flex gap-3 mb-3">
          <Select
            value={uploadJurisdiction}
            onChange={setUploadJurisdiction}
            placeholder="Jurisdiction (optional)"
            options={JURISDICTIONS.map((j) => ({ value: j.value, label: `${j.flag} ${j.label}` }))}
          />
          <Select
            value={uploadDomain}
            onChange={setUploadDomain}
            placeholder="Domain (optional)"
            options={DOMAINS.map((d) => ({ value: d.value, label: d.label }))}
          />
        </div>

        <div
          {...getRootProps()}
          className={cn(
            "border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all",
            isDragActive
              ? "border-[#00d4aa] bg-[rgba(0,212,170,0.06)]"
              : "border-[#2a3040] hover:border-[#4a5568] bg-[#111318]"
          )}
        >
          <input {...getInputProps()} />
          <Upload
            size={32}
            className={cn("mx-auto mb-4", isDragActive ? "text-[#00d4aa]" : "text-[#4a5568]")}
          />
          <p className={cn("text-sm font-semibold mb-1", isDragActive ? "text-[#00d4aa]" : "text-[#8892a4]")}>
            {isDragActive ? "Drop files here…" : "Drag & drop files, or click to browse"}
          </p>
          <p className="text-xs text-[#4a5568]">PDF, DOCX, TXT · Max 50 MB per file</p>
        </div>

        {/* Active uploads */}
        <AnimatePresence>
          {uploading.map((name) => (
            <motion.div
              key={name}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-2 flex items-center gap-3 px-4 py-3 rounded-lg bg-[#111318] border border-[#1f2530]"
            >
              <Loader2 size={14} className="animate-spin text-[#00d4aa]" />
              <span className="text-xs text-[#8892a4] flex-1 truncate">Uploading {name}…</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Documents list */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-mono font-semibold text-[#4a5568] uppercase tracking-widest">
            Your Documents ({docs.length})
          </h2>
          {pending > 0 && (
            <span className="text-xs font-mono text-[#f5a623] flex items-center gap-1">
              <Loader2 size={10} className="animate-spin" /> {pending} processing
            </span>
          )}
        </div>

        {docsQ.isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 size={24} className="animate-spin text-[#4a5568]" />
          </div>
        ) : docs.length === 0 ? (
          <div className="text-center py-16 text-[#4a5568]">
            <FileText size={32} className="mx-auto mb-3 opacity-40" />
            <p className="text-sm font-mono">No documents uploaded yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {docs.map((doc) => (
              <DocumentRow key={doc.id} doc={doc} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function DocumentRow({ doc }: { doc: Document }) {
  const statusIcon = {
    pending: <Loader2 size={14} className="animate-spin text-[#f5a623]" />,
    completed: <CheckCircle size={14} className="text-[#00d4aa]" />,
    failed: <AlertCircle size={14} className="text-[#ff4757]" />,
  }[doc.processing_status] ?? <Clock size={14} className="text-[#4a5568]" />;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex items-center gap-4 px-5 py-3.5 rounded-xl bg-[#111318] border border-[#1f2530] hover:border-[#2a3040] transition-all"
    >
      <FileText size={16} className="text-[#4a5568] flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-[#e8ecf2] truncate">{doc.filename}</p>
        <div className="flex items-center gap-3 mt-0.5 text-[10px] font-mono text-[#4a5568]">
          <span>{formatBytes(doc.file_size_bytes)}</span>
          {doc.jurisdiction && <span>{doc.jurisdiction.toUpperCase()}</span>}
          {doc.domain && <span>{doc.domain.toUpperCase()}</span>}
          {doc.chunk_count != null && <span>{doc.chunk_count} chunks</span>}
          <span>{new Date(doc.created_at).toLocaleDateString()}</span>
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs text-[#4a5568] font-mono">
        {statusIcon}
        <span>{doc.processing_status}</span>
      </div>
    </motion.div>
  );
}

function Select({
  value, onChange, placeholder, options,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none px-3 py-2 pr-8 rounded-lg bg-[#111318] border border-[#2a3040] text-sm text-[#e8ecf2] outline-none focus:border-[#00d4aa] transition-colors cursor-pointer"
      >
        <option value="">{placeholder}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#4a5568] pointer-events-none" />
    </div>
  );
}
