import React, { useState, useEffect } from 'react';
import { Search, Loader2, Award, Zap, BookOpen, Layers, BarChart2, ShieldAlert } from 'lucide-react';
import GraphExplorer from './components/GraphExplorer';

export default function App() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [results, setResults] = useState(null);
  
  // Database status states
  const [dbStatus, setDbStatus] = useState({
    standard: { ingested: false },
    lightrag: { ingested: false, neo4j: { nodes: 0, relationships: 0, status: 'Disconnected' } },
    vector_graph_rag: { ingested: false }
  });

  const BACKEND_URL = 'http://localhost:8000';

  const EXAMPLE_QUERIES = [
    "Compare the national AI investment pledges made by Canada, France, and India.",
    "What is Project Transcendence and which country initiated it?",
    "What does the report say about AI safety and regulation?",
    "Who are the key organizations mentioned in the documents?",
    "What is a large language model?"
  ];

  // Fetch status on mount
  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/status`);
      if (res.ok) {
        const data = await res.json();
        setDbStatus(data);
      }
    } catch (err) {
      console.error("Failed to fetch database status:", err);
    }
  };

  const handleQuery = async (queryText) => {
    const text = queryText || query;
    if (!text.trim()) return;

    setLoading(true);
    setQuery(text);

    try {
      const res = await fetch(`${BACKEND_URL}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text })
      });

      if (res.ok) {
        const data = await res.json();
        setResults(data);
        // Refresh counts if Neo4j is updated
        fetchStatus();
      } else {
        alert("Query failed. Please ensure the backend FastAPI server is running on port 8000.");
      }
    } catch (err) {
      console.error(err);
      alert("Error contacting backend server. Run: uvicorn src.app:app --reload");
    } finally {
      setLoading(false);
    }
  };

  const handleExampleClick = (q) => {
    handleQuery(q);
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col">
      {/* Top Header */}
      <header className="bg-[#0f172a]/95 border-b border-white/5 py-4 px-6 sticky top-0 z-50 backdrop-blur flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-accent flex items-center justify-center font-bold text-darkbg text-lg shadow-lg">
            ⚡
          </div>
          <div>
            <h1 className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              RAG Comparison Dashboard
            </h1>
            <p className="text-xs text-slate-400">
              Benchmarking Standard RAG vs LightRAG vs Zilliz Vector Graph RAG
            </p>
          </div>
        </div>

        {/* Database Hub connection widgets */}
        <div className="flex items-center gap-3 text-xs">
          {/* Standard status */}
          <div className="glass-card px-3 py-1.5 rounded-xl border border-white/5 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-slate-300 font-semibold">Standard:</span>
            <span className="text-slate-400">{dbStatus.standard.ingested ? 'Ingested' : 'Not Loaded'}</span>
          </div>

          {/* VGRAG status */}
          <div className="glass-card px-3 py-1.5 rounded-xl border border-white/5 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-magenta-400 bg-pink-500 animate-pulse" />
            <span className="text-slate-300 font-semibold">Vector Graph:</span>
            <span className="text-slate-400">{dbStatus.vector_graph_rag.ingested ? 'Ingested' : 'Not Loaded'}</span>
          </div>

          {/* LightRAG / Neo4j status */}
          <div className="glass-card px-3 py-1.5 rounded-xl border border-white/5 flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${dbStatus.lightrag.neo4j.status.startsWith('Connected') ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-slate-300 font-semibold">Neo4j AuraDB:</span>
            <span className="text-slate-400">
              {dbStatus.lightrag.neo4j.status.startsWith('Connected') 
                ? `${dbStatus.lightrag.neo4j.nodes} nodes` 
                : 'Offline'}
            </span>
          </div>
        </div>
      </header>

      {/* Tabs Bar */}
      <div className="bg-[#0b0f19] border-b border-white/5 px-6 py-2 flex items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'dashboard' 
                ? 'bg-primary text-darkbg shadow-md' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            📊 Comparative Dashboard
          </button>
          <button
            onClick={() => setActiveTab('graph')}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'graph' 
                ? 'bg-primary text-darkbg shadow-md' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            🕸️ Zilliz Subgraph Explorer (Tab 2)
          </button>
        </div>

        {/* Links to backend pages */}
        <div className="flex gap-3 text-xs font-semibold text-primary">
          <a href={`${BACKEND_URL}/visualizer`} target="_blank" rel="noopener noreferrer" className="hover:underline">
            Full-Screen Visualizer ↗
          </a>
          <span className="text-slate-600">|</span>
          <a href={`${BACKEND_URL}/graph`} target="_blank" rel="noopener noreferrer" className="hover:underline">
            Neo4j Cloud Console ↗
          </a>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        {activeTab === 'dashboard' ? (
          <div className="flex flex-col gap-6">
            {/* Search Input Box */}
            <div className="glass-panel rounded-2xl p-6 relative overflow-hidden">
              <h2 className="text-base font-bold text-slate-200 mb-3 flex items-center gap-2">
                <Zap size={18} className="text-primary" />
                Comparative Search Hub
              </h2>

              <div className="relative">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask a question..."
                  className="w-full bg-[#0b0f19] border border-white/10 rounded-2xl pl-4 pr-12 py-3 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-slate-100 placeholder:text-slate-500"
                  onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
                  disabled={loading}
                />
                <button
                  onClick={() => handleQuery()}
                  disabled={loading}
                  className="absolute right-3 top-2.5 bg-primary hover:bg-[#00f2fe] text-darkbg w-8 h-8 rounded-xl flex items-center justify-center transition-colors disabled:bg-slate-700"
                >
                  {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
                </button>
              </div>

              {/* Example Queries */}
              <div className="mt-4 flex flex-wrap gap-2 items-center">
                <span className="text-xs text-slate-400 font-medium">Try these questions:</span>
                {EXAMPLE_QUERIES.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleExampleClick(q)}
                    disabled={loading}
                    className="bg-white/5 hover:bg-white/10 border border-white/5 rounded-full px-3 py-1 text-[11px] text-slate-300 font-medium transition-colors"
                  >
                    {q.length > 50 ? q.slice(0, 48) + "..." : q}
                  </button>
                ))}
              </div>
            </div>

            {loading && (
              <div className="flex flex-col items-center justify-center p-12 glass-panel rounded-2xl min-h-[300px]">
                <Loader2 size={40} className="text-primary animate-spin mb-3" />
                <p className="font-semibold text-slate-200 text-sm">Querying multi-engine pipelines...</p>
                <p className="text-xs text-slate-400 mt-1 max-w-xs text-center">
                  Standard RAG, LightRAG, and Zilliz Vector Graph RAG are searching concurrently in the background.
                </p>
              </div>
            )}

            {results && !loading && (
              <div className="flex flex-col gap-6">
                {/* AI Referee Winner Panel */}
                <div className="bg-gradient-to-r from-emerald-950/20 to-teal-950/20 border border-emerald-500/20 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 backdrop-blur shadow-lg shadow-emerald-500/5">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 text-xl font-semibold shadow-inner">
                      <Award size={22} />
                    </div>
                    <div>
                      <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider">AI Judge Decision Verdict</span>
                      <h3 className="font-extrabold text-slate-100 text-lg leading-tight mt-0.5">
                        Expected Winner: <span className="bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent">{results.referee.winner}</span>
                      </h3>
                      <p className="text-xs text-slate-300 leading-relaxed mt-2 italic bg-slate-950/20 p-3 border border-white/5 rounded-xl">
                        "{results.referee.reason}"
                      </p>
                    </div>
                  </div>
                </div>

                {/* Performance Benchmarks Grid */}
                <div className="glass-panel rounded-2xl p-6">
                  <h3 className="font-bold text-sm text-slate-200 mb-4 flex items-center gap-2">
                    <BarChart2 size={16} className="text-primary" />
                    Comparative Performance Benchmarks
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Standard Card */}
                    <div className="glass-card rounded-xl p-4 border border-white/5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">🗄️ Standard RAG</span>
                        <span className="text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2 py-0.5 rounded-full font-bold">Standard</span>
                      </div>
                      <div className="mt-3 flex items-baseline gap-1.5">
                        <span className="text-2xl font-black text-cyan-400">{results.standard.latency_ms}</span>
                        <span className="text-xs text-slate-400 font-semibold">ms</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">Ingested chunks used: {results.standard.chunks_used || 0}</p>
                    </div>

                    {/* Light Card */}
                    <div className="glass-card rounded-xl p-4 border border-white/5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">🕸️ LightRAG</span>
                        <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-bold">Graph Hybrid</span>
                      </div>
                      <div className="mt-3 flex items-baseline gap-1.5">
                        <span className="text-2xl font-black text-emerald-400">{results.lightrag.latency_ms}</span>
                        <span className="text-xs text-slate-400 font-semibold">ms</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">Graph nodes traversal logic</p>
                    </div>

                    {/* VGRAG Card */}
                    <div className="glass-card rounded-xl p-4 border border-white/5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">⚡ Vector Graph</span>
                        <span className="text-[10px] bg-pink-500/10 text-pink-400 border border-pink-500/20 px-2 py-0.5 rounded-full font-bold">Vector Triplet</span>
                      </div>
                      <div className="mt-3 flex items-baseline gap-1.5">
                        <span className="text-2xl font-black text-pink-400">{results.vector_graph_rag.latency_ms}</span>
                        <span className="text-xs text-slate-400 font-semibold">ms</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">Milvus Lite entities expanded: {results.vector_graph_rag.chunks_used || 0}</p>
                    </div>
                  </div>
                </div>

                {/* 3-Column Comparative Panels */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Standard Card */}
                  <div className="glass-panel rounded-2xl p-5 flex flex-col min-h-[400px]">
                    <div className="border-b border-white/5 pb-3 mb-3 flex items-center justify-between">
                      <h4 className="font-bold text-sm text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                        <Zap size={16} />
                        Standard RAG Response
                      </h4>
                    </div>
                    <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap flex-1 bg-slate-950/20 p-4 border border-white/5 rounded-xl">
                      {results.standard.answer}
                    </div>

                    {/* Collapsible citation sources */}
                    {results.standard.source_chunks && results.standard.source_chunks.length > 0 && (
                      <div className="mt-4">
                        <h5 className="text-[11px] uppercase font-bold text-slate-400 mb-2">📌 Retrieved Source Chunks</h5>
                        <div className="flex flex-col gap-2 max-h-48 overflow-y-auto pr-1">
                          {results.standard.source_chunks.map((chunk, idx) => (
                            <div key={idx} className="bg-slate-900 border border-white/5 rounded-lg p-2 text-[10px]">
                              <span className="font-bold text-slate-200 block border-b border-white/5 pb-1 mb-1">{chunk.name}</span>
                              <p className="text-slate-400 leading-normal line-clamp-3 hover:line-clamp-none transition-all cursor-pointer">{chunk.content}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* LightRAG Card */}
                  <div className="glass-panel rounded-2xl p-5 flex flex-col min-h-[400px] border-emerald-500/10">
                    <div className="border-b border-white/5 pb-3 mb-3 flex items-center justify-between">
                      <h4 className="font-bold text-sm text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                        <BookOpen size={16} />
                        LightRAG Graph Response
                      </h4>
                    </div>
                    <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap flex-1 bg-slate-950/20 p-4 border border-white/5 rounded-xl">
                      {results.lightrag.answer}
                    </div>
                  </div>

                  {/* VGRAG Card */}
                  <div className="glass-panel rounded-2xl p-5 flex flex-col min-h-[400px] border-pink-500/10">
                    <div className="border-b border-white/5 pb-3 mb-3 flex items-center justify-between">
                      <h4 className="font-bold text-sm text-pink-400 uppercase tracking-wider flex items-center gap-1.5">
                        <Layers size={16} />
                        Vector Graph RAG Response
                      </h4>
                    </div>
                    <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap flex-1 bg-slate-950/20 p-4 border border-white/5 rounded-xl">
                      {results.vector_graph_rag.answer}
                    </div>

                    {/* VGRAG Quick Action to Graph Explorer */}
                    <div className="mt-4 bg-pink-500/5 border border-pink-500/20 rounded-xl p-3 flex items-center justify-between gap-3">
                      <div>
                        <h5 className="text-[10px] font-bold text-pink-400 uppercase">Interactive Graph Synced</h5>
                        <p className="text-[9px] text-slate-400">View exact seed entities and expanded relations</p>
                      </div>
                      <button
                        onClick={() => setActiveTab('graph')}
                        className="bg-pink-500 text-darkbg hover:bg-pink-400 px-3 py-1 rounded-lg text-[10px] font-bold transition-all shadow"
                      >
                        Explore Graph
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {!results && !loading && (
              <div className="flex flex-col items-center justify-center p-12 glass-panel rounded-2xl min-h-[350px] text-center border-dashed border-white/5">
                <span className="text-5xl mb-3">🔍</span>
                <h3 className="font-bold text-base text-slate-200">Ready to Compare Pipelines</h3>
                <p className="text-xs text-slate-400 max-w-sm mt-1 leading-normal">
                  Type a question in the search hub or select one of the query examples to benchmark Standard RAG against LightRAG and Zilliz Vector Graph RAG.
                </p>
              </div>
            )}
          </div>
        ) : (
          <GraphExplorer subgraph={results?.vector_graph_rag?.subgraph} />
        )}
      </main>

      {/* Footer bar */}
      <footer className="bg-[#0b0f19] border-t border-white/5 py-4 px-6 text-center text-xs text-slate-500 mt-auto flex flex-col md:flex-row items-center justify-between gap-2">
        <p>© 2026 Knowledge Hub. High-Fidelity Graph RAG Comparative Ecosystem.</p>
        <p className="text-[10px]">FastAPI Backend Server connected directly to local Milvus Lite and Neo4j AuraDB.</p>
      </footer>
    </div>
  );
}
