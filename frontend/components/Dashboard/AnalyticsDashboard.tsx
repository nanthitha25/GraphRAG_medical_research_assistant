'use client';

import React, { useState, useEffect } from 'react';
import { api, AnalyticsResponse, Interaction } from '../../services/api';
import { RefreshCw, BarChart2, CheckCircle2, ShieldAlert, Heart, Calendar, ArrowRight, UserCheck } from 'lucide-react';

export function AnalyticsDashboard() {
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [analyticsData, interactionsData] = await Promise.all([
        api.getAnalytics(),
        api.getInteractions(30),
      ]);
      setAnalytics(analyticsData);
      setInteractions(interactionsData);
    } catch (err: any) {
      console.error(err);
      setError('Failed to fetch analytics metrics from the database.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="flex flex-col h-full bg-slate-50 overflow-y-auto">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm shrink-0 z-10">
        <div>
          <h2 className="text-xl font-bold text-slate-800">
            RAG Evaluation & Analytics
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Real-time tracking of answer generation accuracy, confidence metrics, hallucination detection rates, and user ratings.
          </p>
        </div>

        <button
          onClick={fetchData}
          className="flex items-center gap-2 text-xs bg-teal-50 text-teal-700 hover:bg-teal-100 font-semibold px-3.5 py-2 rounded-xl transition shadow-sm border border-teal-200/50 self-start"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh Stats
        </button>
      </header>

      {/* Main Content Area */}
      {loading && !analytics ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-3">
          <RefreshCw size={28} className="animate-spin text-teal-600" />
          <span className="text-sm font-semibold text-slate-500">Retrieving system diagnostics...</span>
        </div>
      ) : error ? (
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-sm mx-auto gap-4">
          <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center text-rose-500">
            <ShieldAlert size={28} />
          </div>
          <h3 className="text-base font-bold text-slate-800">Error Fetching Analytics</h3>
          <p className="text-xs text-slate-500 leading-relaxed">{error}</p>
          <button
            onClick={fetchData}
            className="bg-teal-600 text-white font-semibold hover:bg-teal-700 px-4 py-2 rounded-xl text-xs transition shadow-sm"
          >
            Retry
          </button>
        </div>
      ) : (
        <div className="flex-1 max-w-6xl w-full mx-auto p-6 flex flex-col gap-6">
          
          {/* Metrics Overview Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            
            {/* Card 1 */}
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3 text-slate-400">
                <span className="text-[10px] uppercase font-bold tracking-wider">Total Queries</span>
                <BarChart2 size={18} />
              </div>
              <div className="text-3xl font-black text-slate-800">
                {analytics?.total_interactions || 0}
              </div>
              <p className="text-[10px] text-slate-400 mt-1.5 leading-relaxed">
                Total processed clinical questions.
              </p>
            </div>

            {/* Card 2 */}
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3 text-slate-400">
                <span className="text-[10px] uppercase font-bold tracking-wider">Avg Confidence</span>
                <CheckCircle2 size={18} className="text-emerald-500" />
              </div>
              <div className="text-3xl font-black text-slate-800">
                {((analytics?.avg_confidence || 0) * 100).toFixed(0)}%
              </div>
              <p className="text-[10px] text-slate-400 mt-1.5 leading-relaxed">
                Avg LLM output accuracy confidence.
              </p>
            </div>

            {/* Card 3 */}
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3 text-slate-400">
                <span className="text-[10px] uppercase font-bold tracking-wider">Hallucination Rate</span>
                <ShieldAlert size={18} className="text-rose-500" />
              </div>
              <div className="text-3xl font-black text-slate-800">
                {((analytics?.hallucination_rate || 0) * 100).toFixed(0)}%
              </div>
              <p className="text-[10px] text-slate-400 mt-1.5 leading-relaxed">
                Percentage of ungrounded responses flag.
              </p>
            </div>

            {/* Card 4 */}
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3 text-slate-400">
                <span className="text-[10px] uppercase font-bold tracking-wider">Satisfaction Rate</span>
                <Heart size={18} className="text-pink-500" />
              </div>
              <div className="text-3xl font-black text-slate-800">
                {((analytics?.user_satisfaction_rate || 0) * 100).toFixed(0)}%
              </div>
              <p className="text-[10px] text-slate-400 mt-1.5 leading-relaxed">
                Ratio of helpful query votes.
              </p>
            </div>

          </div>

          {/* Detailed interactions table log */}
          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                Interaction History Log
              </h3>
              <span className="text-[10px] text-slate-400 border border-slate-100 px-2 py-0.5 rounded font-semibold bg-slate-50">
                Showing last {interactions.length} queries
              </span>
            </div>

            {interactions.length === 0 ? (
              <div className="p-8 text-center text-slate-400 flex flex-col items-center justify-center gap-2">
                <Calendar size={28} className="text-slate-300" />
                <h4 className="text-xs font-bold text-slate-600">No Interactions Logged</h4>
                <p className="text-[11px] text-slate-500 leading-relaxed max-w-[220px]">
                  Submit queries in the Research Chat interface to view historical logs here.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600 border-collapse">
                  <thead>
                    <tr className="bg-slate-50/50 border-b border-slate-100 text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                      <th className="px-6 py-3 font-semibold">Timestamp</th>
                      <th className="px-6 py-3 font-semibold">Query</th>
                      <th className="px-6 py-3 font-semibold">Confidence</th>
                      <th className="px-6 py-3 font-semibold">Hallucination</th>
                      <th className="px-6 py-3 font-semibold">Feedback</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {interactions.map((it, idx) => {
                      const date = it.timestamp ? new Date(it.timestamp).toLocaleString() : 'N/A';
                      const isHallucinated = it.hallucination_score > 0.4;
                      
                      return (
                        <tr key={it.id || idx} className="hover:bg-slate-50/30 transition-colors">
                          <td className="px-6 py-4 whitespace-nowrap text-slate-400 font-mono text-[10px]">
                            {date}
                          </td>
                          <td className="px-6 py-4 max-w-xs truncate font-medium text-slate-700" title={it.query}>
                            {it.query}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap font-bold text-slate-800">
                            {((it.confidence || 0) * 100).toFixed(0)}%
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              isHallucinated 
                                ? 'bg-rose-50 text-rose-700 border border-rose-100' 
                                : 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                            }`}>
                              {it.hallucination_score.toFixed(2)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap capitalize font-semibold">
                            {it.feedback === 'helpful' && (
                              <span className="text-emerald-600 flex items-center gap-1.5">
                                <UserCheck size={14} /> Helpful
                              </span>
                            )}
                            {it.feedback === 'inaccurate' && (
                              <span className="text-amber-600">Inaccurate</span>
                            )}
                            {it.feedback === 'hallucinated' && (
                              <span className="text-rose-600">Hallucinated</span>
                            )}
                            {(!it.feedback || it.feedback === 'none') && (
                              <span className="text-slate-400">None</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
