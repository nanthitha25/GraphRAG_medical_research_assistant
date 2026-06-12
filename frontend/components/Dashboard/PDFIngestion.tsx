'use client';

import React, { useState, useCallback } from 'react';
import { api, UploadResponse } from '../../services/api';
import { FileUp, Loader2, CheckCircle2, AlertTriangle, FileText, Database, ShieldAlert, Cpu } from 'lucide-react';

export function PDFIngestion() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const processFile = async (selectedFile: File) => {
    if (selectedFile.type !== 'application/pdf') {
      setError('Only PDF documents are supported for clinical ingestion.');
      setFile(null);
      return;
    }
    
    setFile(selectedFile);
    setError(null);
    setResult(null);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || uploading) return;

    setUploading(true);
    setError(null);
    try {
      const response = await api.upload(file);
      if (response.success) {
        setResult(response);
        setFile(null); // Clear input
      } else {
        setError(response.error || 'Ingestion failed during processing. Check logs.');
      }
    } catch (err: any) {
      console.error(err);
      setError(
        err?.response?.data?.detail || 
        'An error occurred uploading the file. Ensure the backend is reachable and within file limits.'
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 overflow-y-auto">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 shadow-sm shrink-0">
        <h2 className="text-xl font-bold text-slate-800">
          Medical Research Ingestion Portal
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Upload PDF clinical literature and research papers to build the vector index and update the Neo4j graph structure.
        </p>
      </header>

      {/* Main Content */}
      <div className="flex-1 max-w-4xl w-full mx-auto p-6 flex flex-col gap-6">
        
        {/* Upload form card */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-sm font-bold text-slate-800 mb-4 uppercase tracking-wider">
            Upload Document
          </h3>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {/* Drag Zone */}
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-2xl p-8 text-center flex flex-col items-center justify-center cursor-pointer transition relative min-h-[220px] ${
                dragActive 
                  ? 'border-teal-500 bg-teal-50/30' 
                  : 'border-slate-200 hover:border-teal-500/50 hover:bg-slate-50/50'
              }`}
              onClick={() => document.getElementById('file-upload-input')?.click()}
            >
              <input
                id="file-upload-input"
                type="file"
                className="hidden"
                accept=".pdf"
                onChange={handleChange}
                disabled={uploading}
              />

              {uploading ? (
                <div className="flex flex-col items-center gap-3">
                  <Loader2 className="animate-spin text-teal-600" size={36} />
                  <span className="text-sm font-bold text-slate-700 animate-pulse">
                    Ingesting clinical document...
                  </span>
                  <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
                    This indexes text chunks, calls Gemini to extract entities/relationships, and populates the graph database.
                  </p>
                </div>
              ) : file ? (
                <div className="flex flex-col items-center gap-3">
                  <FileText className="text-teal-600 animate-bounce" size={40} />
                  <span className="text-sm font-bold text-slate-700 max-w-sm truncate">
                    {file.name}
                  </span>
                  <span className="text-xs text-slate-400">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </span>
                  <span className="text-xs font-semibold bg-teal-50 border border-teal-200/50 text-teal-700 px-3 py-1 rounded-full mt-1.5">
                    Click to change file
                  </span>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <FileUp className="text-slate-400 group-hover:text-teal-500" size={42} />
                  <span className="text-sm font-bold text-slate-700">
                    Drag and drop your PDF here
                  </span>
                  <span className="text-xs text-slate-400">
                    or click to browse from files
                  </span>
                  <p className="text-[10px] text-slate-400 border border-slate-100 rounded bg-slate-50 px-2 py-0.5 mt-4">
                    Clinical Research Papers, Guidelines, or Studies (.PDF)
                  </p>
                </div>
              )}
            </div>

            {/* Error Message */}
            {error && (
              <div className="flex items-start gap-3 p-4 bg-rose-50 border border-rose-100 rounded-2xl text-xs text-rose-700 leading-relaxed font-semibold">
                <ShieldAlert className="shrink-0 text-rose-600 mt-0.5" size={16} />
                <span>{error}</span>
              </div>
            )}

            {/* Submit button */}
            {file && !uploading && (
              <button
                type="submit"
                className="bg-teal-600 hover:bg-teal-700 text-white font-bold py-3 px-6 rounded-2xl shadow-md transition self-end text-sm"
              >
                Start Ingestion
              </button>
            )}
          </form>
        </div>

        {/* Processing details cards on Success */}
        {result && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex flex-col gap-5">
            <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
              <div className="w-10 h-10 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                <CheckCircle2 size={24} />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-slate-800">
                  Clinical Ingestion Successful
                </h3>
                <p className="text-xs text-slate-400 truncate max-w-lg mt-0.5">
                  Processed and integrated: <strong className="text-slate-600">{result.filename}</strong>
                </p>
              </div>
            </div>

            {/* Grid display */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              
              {/* Card 1 */}
              <div className="bg-slate-50/50 hover:bg-slate-50 border border-slate-100 rounded-2xl p-4 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Chunks Indexed</span>
                  <Database size={16} className="text-slate-400" />
                </div>
                <div className="text-2xl font-black text-slate-800">{result.chunks_indexed}</div>
                <div className="text-[10px] text-slate-400 mt-1">Vector DB embeddings</div>
              </div>

              {/* Card 2 */}
              <div className="bg-slate-50/50 hover:bg-slate-50 border border-slate-100 rounded-2xl p-4 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Entities Extracted</span>
                  <Cpu size={16} className="text-slate-400" />
                </div>
                <div className="text-2xl font-black text-slate-800">{result.entities_found}</div>
                <div className="text-[10px] text-slate-400 mt-1">LLM identified concepts</div>
              </div>

              {/* Card 3 */}
              <div className="bg-slate-50/50 hover:bg-slate-50 border border-slate-100 rounded-2xl p-4 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Relations Extracted</span>
                  <Cpu size={16} className="text-slate-400" />
                </div>
                <div className="text-2xl font-black text-slate-800">{result.relationships_found}</div>
                <div className="text-[10px] text-slate-400 mt-1">Semantic connections</div>
              </div>

              {/* Card 4 */}
              <div className="bg-slate-50/50 hover:bg-slate-50 border border-slate-100 rounded-2xl p-4 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Nodes Created</span>
                  <CheckCircle2 size={16} className="text-slate-400" />
                </div>
                <div className="text-2xl font-black text-slate-800">{result.graph_nodes_created}</div>
                <div className="text-[10px] text-slate-400 mt-1">Graph DB properties</div>
              </div>

            </div>

            {/* Ingestion performance footer */}
            <div className="text-[11px] text-slate-400 bg-slate-50 rounded-xl p-3.5 border border-slate-100 flex items-center justify-between">
              <span>RAG pipeline successfully indexed clinical data in memory databases.</span>
              <span className="font-semibold text-slate-600">Time elapsed: {result.duration_seconds.toFixed(2)}s</span>
            </div>

          </div>
        )}

      </div>
    </div>
  );
}
