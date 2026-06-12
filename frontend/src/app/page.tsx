'use client';

import React, { useState } from 'react';
import { MessageSquare, Network, FileUp, BarChart2, Cpu } from 'lucide-react';
import { ChatInterface } from '../../components/Chat/ChatInterface';
import { GraphExplorer } from '../../components/Dashboard/GraphExplorer';
import { PDFIngestion } from '../../components/Dashboard/PDFIngestion';
import { AnalyticsDashboard } from '../../components/Dashboard/AnalyticsDashboard';

type Tab = 'chat' | 'graph' | 'ingestion' | 'analytics';

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>('chat');

  return (
    <main className="h-screen w-full flex bg-slate-100 overflow-hidden">
      
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0">
        {/* Brand Header */}
        <div className="px-6 py-5 border-b border-slate-800 flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-teal-500 text-slate-950 flex items-center justify-center shadow-md">
            <Cpu size={18} className="stroke-[2.5]" />
          </div>
          <div>
            <h1 className="font-extrabold text-sm text-white tracking-wider uppercase">
              Clinical GraphRAG
            </h1>
            <span className="text-[10px] font-bold text-teal-400">
              v2.0 Assistant
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex-1 px-4 py-6 flex flex-col gap-2">
          {/* Chat Tab */}
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-extrabold transition-all ${
              activeTab === 'chat'
                ? 'bg-teal-600 text-white shadow-md shadow-teal-900/30'
                : 'hover:bg-slate-800/80 hover:text-slate-100 text-slate-400'
            }`}
          >
            <MessageSquare size={16} />
            Research Chat
          </button>

          {/* Graph Explorer Tab */}
          <button
            onClick={() => setActiveTab('graph')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-extrabold transition-all ${
              activeTab === 'graph'
                ? 'bg-teal-600 text-white shadow-md shadow-teal-900/30'
                : 'hover:bg-slate-800/80 hover:text-slate-100 text-slate-400'
            }`}
          >
            <Network size={16} />
            Graph Explorer
          </button>

          {/* Ingestion Tab */}
          <button
            onClick={() => setActiveTab('ingestion')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-extrabold transition-all ${
              activeTab === 'ingestion'
                ? 'bg-teal-600 text-white shadow-md shadow-teal-900/30'
                : 'hover:bg-slate-800/80 hover:text-slate-100 text-slate-400'
            }`}
          >
            <FileUp size={16} />
            Ingest Documents
          </button>

          {/* Analytics Tab */}
          <button
            onClick={() => setActiveTab('analytics')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-extrabold transition-all ${
              activeTab === 'analytics'
                ? 'bg-teal-600 text-white shadow-md shadow-teal-900/30'
                : 'hover:bg-slate-800/80 hover:text-slate-100 text-slate-400'
            }`}
          >
            <BarChart2 size={16} />
            Analytics & Logs
          </button>
        </nav>

        {/* Footer Brand Info */}
        <div className="p-4 border-t border-slate-800 text-[10px] text-slate-500 font-bold text-center">
          SELF-IMPROVING CLINICAL AI
        </div>
      </aside>

      {/* Main Tab Render Workspace */}
      <section className="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-50 relative">
        <div className={`flex-1 h-full w-full ${activeTab === 'chat' ? 'block' : 'hidden'}`}>
          <ChatInterface />
        </div>
        <div className={`flex-1 h-full w-full ${activeTab === 'graph' ? 'block' : 'hidden'}`}>
          <GraphExplorer />
        </div>
        <div className={`flex-1 h-full w-full ${activeTab === 'ingestion' ? 'block' : 'hidden'}`}>
          <PDFIngestion />
        </div>
        <div className={`flex-1 h-full w-full ${activeTab === 'analytics' ? 'block' : 'hidden'}`}>
          <AnalyticsDashboard />
        </div>
      </section>

    </main>
  );
}
