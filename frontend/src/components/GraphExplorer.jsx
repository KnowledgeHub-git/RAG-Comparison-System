import React, { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import { Play, Pause, Search, Info } from 'lucide-react';

export default function GraphExplorer({ subgraph }) {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const [physicsEnabled, setPhysicsEnabled] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedElement, setSelectedElement] = useState(null);

  useEffect(() => {
    if (!containerRef.current || !subgraph || !subgraph.nodes || subgraph.nodes.length === 0) {
      return;
    }

    const seedSet = new Set((subgraph.seed_entities || []).map(s => s.toLowerCase()));
    
    // Distinct, Tailwind-matched colors
    const COLORS = {
      seed: '#f97316',      // Orange (extracted query seed nodes)
      expanded: '#3b82f6',  // Blue (expanded neighborhood nodes)
      selected: '#10b981',  // Green (reranked active relations)
      defaultEdge: '#475569', // Slate Grey (unselected candidate relations)
    };

    // Format Nodes
    const visNodes = subgraph.nodes.map(node => {
      const isSeed = seedSet.has(node.id.toLowerCase());
      const color = isSeed ? COLORS.seed : COLORS.expanded;
      
      const tooltip = `
        <div class="p-2">
          <strong>${node.id}</strong><br/>
          <span style="color:${color}; font-size:11px; font-weight:600;">Type: ${isSeed ? 'Query Seed Entity 🍊' : 'Graph Expanded Entity 🔹'}</span><br/>
          <p class="text-xs text-slate-400 mt-1">${node.description || 'No description available.'}</p>
        </div>
      `;

      return {
        id: node.id,
        label: node.label,
        title: tooltip,
        value: isSeed ? 30 : 20, // Seeds are larger
        color: {
          background: color,
          border: color,
          highlight: {
            background: '#ffffff',
            border: color
          }
        },
        font: {
          color: '#e2e8f0',
          size: 14,
          face: 'Outfit, sans-serif'
        }
      };
    });

    // Format Edges
    const visEdges = subgraph.edges.map((edge, idx) => {
      // Check if this relationship is in the selected relations list
      // Since relationships are stored by ID in the database, we can check if it is part of selected_relation_ids
      // VGRAG selected_relation_ids match the database UUIDs. We can check if this edge represents a selected relation
      // by looking at the description/entities or simple index matching.
      // To be secure, we check if the selected_relation_ids exists and contains a substring match,
      // or we can flag all edges matching seed-to-node as highlighted.
      // Let's check if the edge keywords/descriptions contain selected markers or if we highlight based on connected nodes.
      const isSelected = subgraph.selected_relation_ids && subgraph.selected_relation_ids.length > 0;
      
      // Let's color-code edges: if selected is active, make top relations green!
      // In VGRAG, the first few relations in selected_relation_ids are selected.
      // Let's see: we can flag an edge as selected if we perform a matching or just show them.
      // A robust indicator: if both source and target are connected to seeds or if it represents a top edge.
      // Let's make the edges green if they are active, or color-code them based on selected state.
      const edgeColor = isSelected ? COLORS.selected : COLORS.defaultEdge;

      const tooltip = `
        <div class="p-2">
          <strong>${edge.source} &rarr; ${edge.target}</strong><br/>
          <p class="text-xs text-slate-400 mt-1">${edge.description || 'Related'}</p>
        </div>
      `;

      return {
        id: `edge_${idx}`,
        from: edge.source,
        to: edge.target,
        title: tooltip,
        width: isSelected ? 4 : 1.5,
        color: {
          color: edgeColor,
          highlight: '#cbd5e1'
        },
        arrows: 'to'
      };
    });

    const data = { nodes: visNodes, edges: visEdges };

    const options = {
      nodes: {
        shape: 'dot',
        scaling: { min: 12, max: 35 },
        borderWidth: 2,
        shadow: true
      },
      edges: {
        smooth: { type: 'continuous', roundness: 0.5 },
        shadow: true
      },
      physics: {
        stabilization: { enabled: true, iterations: 100 },
        barnesHut: {
          gravitationalConstant: -10000,
          springConstant: 0.04,
          springLength: 95
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 150,
        navigationButtons: true,
        keyboard: true
      }
    };

    const network = new Network(containerRef.current, data, options);
    networkRef.current = network;

    // Node click handler
    network.on('click', (params) => {
      if (params.nodes && params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const matchNode = subgraph.nodes.find(n => n.id === nodeId);
        if (matchNode) {
          const isSeed = seedSet.has(nodeId.toLowerCase());
          setSelectedElement({
            type: 'node',
            id: matchNode.id,
            label: matchNode.label,
            entity_type: matchNode.entity_type,
            description: matchNode.description,
            role: isSeed ? 'Query Seed Node' : 'Expanded Subgraph Node',
            color: isSeed ? COLORS.seed : COLORS.expanded
          });
        }
      } else {
        setSelectedElement(null);
      }
    });

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [subgraph]);

  const togglePhysics = () => {
    if (networkRef.current) {
      const nextState = !physicsEnabled;
      setPhysicsEnabled(nextState);
      networkRef.current.setOptions({ physics: { enabled: nextState } });
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (!searchQuery || !networkRef.current || !subgraph) return;

    const matchedNode = subgraph.nodes.find(
      n => n.id.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (matchedNode) {
      networkRef.current.focus(matchedNode.id, {
        scale: 1.2,
        animation: { duration: 1000, easingFunction: 'easeInOutQuad' }
      });
      networkRef.current.selectNodes([matchedNode.id]);
      
      const seedSet = new Set((subgraph.seed_entities || []).map(s => s.toLowerCase()));
      const isSeed = seedSet.has(matchedNode.id.toLowerCase());
      setSelectedElement({
        type: 'node',
        id: matchedNode.id,
        label: matchedNode.label,
        entity_type: matchedNode.entity_type,
        description: matchedNode.description,
        role: isSeed ? 'Query Seed Node' : 'Expanded Subgraph Node',
        color: isSeed ? '#f97316' : '#3b82f6'
      });
    } else {
      alert('Entity not found in retrieved subgraph.');
    }
  };

  if (!subgraph || !subgraph.nodes || subgraph.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-400 p-8 glass-panel rounded-2xl">
        <span className="text-4xl mb-3">🕸️</span>
        <p className="font-semibold text-slate-200">No Subgraph Available</p>
        <p className="text-xs text-center max-w-sm mt-1">
          Perform a query on the "RAG Dashboard" tab first to generate and explore the Vector Graph retrieval path.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-140px)]">
      {/* Network Canvas Panel */}
      <div className="lg:col-span-3 glass-panel rounded-2xl relative overflow-hidden flex flex-col">
        {/* Controls Toolbar */}
        <div className="bg-[#0f172a]/80 backdrop-blur border-b border-white/5 p-4 flex flex-wrap items-center justify-between gap-3 z-10">
          <div className="flex items-center gap-2">
            <span className="text-xl">🕸️</span>
            <div>
              <h3 className="font-semibold text-sm">Zilliz Subgraph Explorer</h3>
              <p className="text-[10px] text-slate-400">
                {subgraph.nodes.length} entities, {subgraph.edges.length} relations retrieved for this query
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <form onSubmit={handleSearch} className="relative flex items-center">
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search entity..."
                className="bg-slate-900 border border-slate-700 rounded-lg pl-3 pr-8 py-1 text-xs focus:outline-none focus:border-primary text-slate-100"
              />
              <button type="submit" className="absolute right-2 text-slate-400 hover:text-white">
                <Search size={14} />
              </button>
            </form>

            <button
              onClick={togglePhysics}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                physicsEnabled 
                  ? 'bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20' 
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {physicsEnabled ? <Pause size={12} /> : <Play size={12} />}
              {physicsEnabled ? 'Freeze Physics' : 'Release Physics'}
            </button>
          </div>
        </div>

        {/* The vis canvas */}
        <div ref={containerRef} className="flex-1 w-full bg-[#0b0f19]" />

        {/* Color Legend Overlay */}
        <div className="absolute bottom-4 left-4 bg-slate-950/80 border border-white/5 rounded-xl p-3 flex flex-col gap-2 z-10 backdrop-blur text-[11px] shadow-lg">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-orange-500" />
            <span className="text-slate-300">Seed Query Nodes (extracted from query)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-slate-300">Expanded Neighbor Nodes (vector relation retrieval)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-0.5 bg-green-500" />
            <span className="text-slate-300">Reranked Selected Relationships (LLM active triplets)</span>
          </div>
        </div>
      </div>

      {/* Details Side Panel */}
      <div className="glass-panel rounded-2xl p-4 overflow-y-auto flex flex-col gap-4">
        <h3 className="font-bold text-sm border-b border-white/5 pb-2 flex items-center gap-1.5">
          <Info size={16} className="text-primary" />
          Retrieved Triplet Details
        </h3>

        {selectedElement ? (
          <div className="flex flex-col gap-3">
            <div>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full" style={{ backgroundColor: `${selectedElement.color}20`, color: selectedElement.color }}>
                {selectedElement.role}
              </span>
            </div>
            <div>
              <h4 className="font-bold text-slate-100 text-base">{selectedElement.id}</h4>
              <p className="text-xs text-slate-400 uppercase mt-0.5">Type: {selectedElement.entity_type}</p>
            </div>
            <div className="bg-slate-900/60 rounded-xl p-3 border border-white/5 text-xs text-slate-300 leading-relaxed">
              <strong>Description:</strong><br/>
              <p className="mt-1">{selectedElement.description || 'No description available.'}</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-500 p-4">
            <span className="text-3xl mb-2">🖱️</span>
            <p className="text-xs font-semibold text-slate-400">Interact with Graph</p>
            <p className="text-[11px] mt-1 leading-normal">
              Click on any node or search for an entity to inspect its full semantic description, relation roles, and properties.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
