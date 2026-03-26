import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Loader2, BookOpen, ChevronDown, ChevronUp, Zap, StopCircle } from "lucide-react";
import toast from "react-hot-toast";
import { useAppStore } from "@/stores/appStore";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils";

const API_BASE = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : "/api/v1";

type Citation = { regulation_name: string; jurisdiction: string; section?: string; relevance_score: number };
type QueryResult = {
  answer: string;
  citations: Citation[];
  confidence: number;
  caveats: string[];
  next_steps: string[];
  regulatory_bodies: string[];
  latency_ms: number;
  sources_used: number;
  query_id?: string;
};

const EXAMPLE_QUERIES = [
  "What are the labeling requirements for health supplements in South Korea?",
  "Compare maximum sodium benzoate limits in EU vs India vs UAE",
  "What is the licensing pathway for a Class II medical device in Brazil?",
  "Is titanium dioxide (E171) permitted in food products in the United States?",
  "What mandatory allergens must be declared on packaged food in New Zealand?",
];

export default function QueryPage() {
  const { selectedJurisdiction, selectedDomain } = useAppStore();
  const { token } = useAuthStore();
  const [query, setQuery] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamedText, setStreamedText] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [showCitations, setShowCitations] = useState(false);
  const [history, setHistory] = useState<Array<{ query: string; result: QueryResult }>>([]);
  const cancelRef = useRef<(() => void) | null>(null);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const responseRef = useRef<HTMLDivElement>(null);

  // Auto-scroll as tokens stream in
  useEffect(() => {
    if (streaming && responseRef.current) {
      responseRef.current.scrollTop = responseRef.current.scrollHeight;
    }
  }, [streamedText, streaming]);

  const handleSubmit = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query.trim() || streaming) return;

    setStreaming(true);
    setStreamedText("");
    setResult(null);
    setStatusMessage("Connecting…");
    setShowCitations(false);

    let cancelled = false;
    let fullText = "";

    try {
      const response = await fetch(`${API_BASE}/query/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          Accept: "text/event-stream",
        },
        body: JSON.stringify({
          query: query.trim(),
          jurisdiction: selectedJurisdiction || undefined,
          domain: selectedDomain || undefined,
        }),
        signal: (() => {
          const ctrl = new AbortController();
          cancelRef.current = () => { cancelled = true; ctrl.abort(); };
          return ctrl.signal;
        })(),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Request failed" }));
        const msg = typeof err.detail === "string" ? err.detail : "Query failed";
        if (response.status === 429 && typeof err.detail === "object") {
          toast.error(`Daily limit reached: ${err.detail.used}/${err.detail.limit} queries used`);
        } else {
          toast.error(msg);
        }
        setStreaming(false);
        setStatusMessage("");
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) { toast.error("Streaming not supported"); setStreaming(false); return; }

      const decoder = new TextDecoder();

      while (!cancelled) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6);
          if (raw === "[DONE]") { cancelled = true; break; }

          try {
            const event = JSON.parse(raw);
            if (event.type === "status") {
              setStatusMessage(event.message);
            } else if (event.type === "token") {
              fullText += event.token;
              // Strip trailing JSON block from displayed text
              const display = fullText.replace(/```json[\s\S]*?```\s*$/g, "").trim();
              setStreamedText(display);
              setStatusMessage("");
            } else if (event.type === "done") {
              setResult({
                answer: fullText.replace(/```json[\s\S]*?```\s*$/g, "").trim(),
                citations: event.citations || [],
                confidence: event.confidence || 0.7,
                caveats: event.caveats || [],
                next_steps: event.next_steps || [],
                regulatory_bodies: event.regulatory_bodies || [],
                latency_ms: event.latency_ms || 0,
                sources_used: event.sources_used || 0,
                query_id: event.query_id,
              });
            } else if (event.type === "error") {
              toast.error(event.message || "Stream error");
            }
          } catch { /* non-JSON line, ignore */ }
        }
      }

      // If we got text but no done event
      if (fullText && !result) {
        setResult({ answer: fullText.replace(/```json[\s\S]*?```\s*$/g, "").trim(),
          citations: [], confidence: 0.7, caveats: [], next_steps: [],
          regulatory_bodies: [], latency_ms: 0, sources_used: 0 });
      }

      // Add to history
      if (fullText.trim()) {
        setHistory(h => [{
          query: query.trim(),
          result: { answer: fullText.replace(/```json[\s\S]*?```\s*$/g, "").trim(),
            citations: [], confidence: 0.7, caveats: [], next_steps: [],
            regulatory_bodies: [], latency_ms: 0, sources_used: 0 },
        }, ...h].slice(0, 10));
      }
    } catch (err: any) {
      if (err?.name !== "AbortError") {
        toast.error("Query failed. Please try again.");
      }
    } finally {
      setStreaming(false);
      setStatusMessage("");
      cancelRef.current = null;
    }
  }, [query, streaming, selectedJurisdiction, selectedDomain, token]);

  const handleCancel = () => { cancelRef.current?.(); };

  const confidenceColor = (c: number) => c >= 0.8 ? "#00d4aa" : c >= 0.6 ? "#f5a623" : "#ff4757";

  return (
    <div className="flex h-full">
      {/* Main query area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="border-b border-[#1f2530] px-6 py-4">
          <h1 className="text-lg font-bold text-[#e8ecf2]">AI Query</h1>
          <p className="text-xs text-[#4a5568] mt-0.5">Ask any regulatory compliance question</p>
        </div>

        <div className="flex-1 overflow-y-auto" ref={responseRef}>
          {/* Example queries */}
          {!streamedText && !result && !streaming && (
            <div className="px-6 py-6">
              <p className="text-xs text-[#4a5568] mb-3 font-mono uppercase tracking-widest">Try asking</p>
              <div className="space-y-2">
                {EXAMPLE_QUERIES.map(q => (
                  <button key={q} onClick={() => { setQuery(q); textAreaRef.current?.focus(); }}
                    className="w-full text-left px-4 py-3 rounded-xl bg-[#111318] border border-[#1f2530] hover:border-[#2a3040] text-xs text-[#8892a4] hover:text-[#e8ecf2] transition-all">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Streaming response */}
          {(streaming || streamedText || result) && (
            <div className="px-6 py-6">
              {/* Status indicator */}
              {statusMessage && (
                <div className="flex items-center gap-2 mb-4">
                  <Loader2 size={13} className="animate-spin text-[#00d4aa]" />
                  <span className="text-xs text-[#8892a4]">{statusMessage}</span>
                </div>
              )}

              {/* Answer text */}
              {(streamedText || result?.answer) && (
                <div className="prose-invert prose-sm max-w-none mb-5">
                  <div className="text-sm leading-relaxed text-[#d4d8e0] whitespace-pre-wrap">
                    {result?.answer || streamedText}
                    {streaming && !statusMessage && (
                      <span className="inline-block w-2 h-4 bg-[#00d4aa] ml-0.5 animate-pulse rounded-sm" />
                    )}
                  </div>
                </div>
              )}

              {/* Metadata */}
              {result && !streaming && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
                  {/* Stats bar */}
                  <div className="flex items-center gap-4 flex-wrap">
                    <span className="flex items-center gap-1.5 text-[10px]">
                      <span className="w-2 h-2 rounded-full" style={{ background: confidenceColor(result.confidence) }} />
                      <span style={{ color: confidenceColor(result.confidence) }} className="font-mono font-bold">
                        {Math.round(result.confidence * 100)}% confidence
                      </span>
                    </span>
                    <span className="text-[10px] text-[#4a5568] font-mono">{result.sources_used} sources</span>
                    <span className="text-[10px] text-[#4a5568] font-mono">{result.latency_ms}ms</span>
                    {result.query_id && (
                      <span className="text-[9px] text-[#2a3040] font-mono">ID: {result.query_id.slice(0,8)}</span>
                    )}
                  </div>

                  {/* Citations */}
                  {result.citations.length > 0 && (
                    <div className="bg-[#111318] border border-[#1f2530] rounded-xl overflow-hidden">
                      <button onClick={() => setShowCitations(v => !v)}
                        className="w-full flex items-center justify-between px-4 py-2.5 text-xs text-[#8892a4] hover:text-[#e8ecf2] transition-colors">
                        <span className="flex items-center gap-2"><BookOpen size={12} /> {result.citations.length} citations</span>
                        {showCitations ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                      {showCitations && (
                        <div className="border-t border-[#1f2530] divide-y divide-[#1f2530]">
                          {result.citations.map((c, i) => (
                            <div key={i} className="px-4 py-2.5">
                              <div className="text-xs font-semibold text-[#e8ecf2]">{c.regulation_name}</div>
                              <div className="text-[10px] text-[#4a5568] mt-0.5">
                                {c.jurisdiction.toUpperCase()}{c.section ? ` · ${c.section}` : ""}
                                {c.relevance_score ? ` · ${Math.round(c.relevance_score * 100)}% relevant` : ""}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Caveats */}
                  {result.caveats.length > 0 && (
                    <div className="bg-[rgba(245,166,35,0.06)] border border-[rgba(245,166,35,0.2)] rounded-xl px-4 py-3">
                      <p className="text-[10px] font-bold text-[#f5a623] mb-1.5 uppercase tracking-wider">Important caveats</p>
                      {result.caveats.map((c, i) => <p key={i} className="text-xs text-[#d4a96a] leading-relaxed">• {c}</p>)}
                    </div>
                  )}

                  {/* Next steps */}
                  {result.next_steps.length > 0 && (
                    <div className="bg-[rgba(0,212,170,0.04)] border border-[rgba(0,212,170,0.15)] rounded-xl px-4 py-3">
                      <p className="text-[10px] font-bold text-[#00d4aa] mb-1.5 uppercase tracking-wider">Suggested next steps</p>
                      {result.next_steps.map((s, i) => <p key={i} className="text-xs text-[#8892a4] leading-relaxed">→ {s}</p>)}
                    </div>
                  )}
                </motion.div>
              )}
            </div>
          )}
        </div>

        {/* Input form */}
        <div className="border-t border-[#1f2530] p-4">
          {/* Active filters */}
          {(selectedJurisdiction || selectedDomain) && (
            <div className="flex gap-1.5 mb-2">
              {selectedJurisdiction && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-[rgba(0,212,170,0.08)] text-[#00d4aa] border border-[rgba(0,212,170,0.2)] font-mono">
                  {selectedJurisdiction}
                </span>
              )}
              {selectedDomain && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-[rgba(102,153,255,0.08)] text-[#6699ff] border border-[rgba(102,153,255,0.2)] font-mono">
                  {selectedDomain}
                </span>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="relative">
            <textarea
              ref={textAreaRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
              placeholder="Ask a regulatory compliance question… (Enter to send, Shift+Enter for new line)"
              rows={3}
              disabled={streaming}
              className={cn(
                "w-full px-4 py-3 pr-20 bg-[#111318] border rounded-2xl text-sm text-[#e8ecf2] placeholder-[#4a5568] outline-none resize-none transition-all",
                streaming ? "border-[#2a3040] opacity-60" : "border-[#2a3040] focus:border-[#00d4aa]"
              )}
            />
            <div className="absolute right-3 bottom-3 flex gap-1.5">
              {streaming && (
                <button type="button" onClick={handleCancel}
                  className="p-2 rounded-xl bg-[rgba(255,71,87,0.12)] text-[#ff4757] hover:bg-[rgba(255,71,87,0.2)] transition-colors"
                  title="Cancel">
                  <StopCircle size={15} />
                </button>
              )}
              <button type="submit" disabled={!query.trim() || streaming}
                className={cn("p-2 rounded-xl transition-all",
                  query.trim() && !streaming
                    ? "bg-[#00d4aa] text-black hover:bg-[#00bfa5] active:scale-95"
                    : "bg-[#1f2530] text-[#4a5568] cursor-not-allowed")}>
                {streaming ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
              </button>
            </div>
          </form>
          <p className="text-[9px] text-[#2a3040] mt-2 text-center font-mono">
            RegulAI provides guidance only. Always verify with a qualified regulatory professional.
          </p>
        </div>
      </div>

      {/* History sidebar */}
      {history.length > 0 && (
        <div className="w-64 border-l border-[#1f2530] flex flex-col hidden lg:flex">
          <div className="px-4 py-3 border-b border-[#1f2530]">
            <span className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest">Recent queries</span>
          </div>
          <div className="flex-1 overflow-y-auto">
            {history.map((h, i) => (
              <button key={i} onClick={() => { setQuery(h.query); setResult(h.result); setStreamedText(h.result.answer); }}
                className="w-full text-left px-4 py-3 border-b border-[#1f2530] hover:bg-[#111318] transition-colors">
                <p className="text-xs text-[#8892a4] line-clamp-2 leading-relaxed">{h.query}</p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
