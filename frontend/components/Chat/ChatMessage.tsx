import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Bot, ThumbsUp, ThumbsDown, ShieldAlert, FileText, CheckCircle2 } from 'lucide-react';
import { api } from '../../services/api';

export interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  confidence?: number;
  hallucination_score?: number;
  supported?: boolean;
  sources?: Array<{
    source_name?: string;
    text_snippet?: string;
    score?: number;
    [key: string]: any;
  }>;
  interaction_id?: number;
}

export function ChatMessage({ 
  role, 
  content, 
  confidence, 
  hallucination_score, 
  supported, 
  sources,
  interaction_id 
}: ChatMessageProps) {
  const isUser = role === 'user';
  
  // Rating state
  const [rating, setRating] = useState<'helpful' | 'inaccurate' | 'hallucinated' | null>(null);
  const [ratingSubmitted, setRatingSubmitted] = useState(false);

  const handleRating = async (type: 'helpful' | 'inaccurate' | 'hallucinated') => {
    if (!interaction_id || ratingSubmitted) return;
    
    setRating(type);
    try {
      await api.submitFeedback(interaction_id, type);
      setRatingSubmitted(true);
    } catch (error) {
      console.error('Failed to submit rating feedback:', error);
      // Reset if failed
      setRating(null);
    }
  };

  const isLowConfidence = confidence !== undefined && confidence < 0.6;
  const isHallucinatedAlert = hallucination_score !== undefined && hallucination_score > 0.4;

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      <div className={`flex max-w-[85%] ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start gap-4`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center shadow-sm ${
          isUser ? 'bg-blue-600 text-white' : 'bg-teal-600 text-white'
        }`}>
          {isUser ? <User size={18} /> : <Bot size={18} />}
        </div>

        {/* Message Bubble Column */}
        <div className="flex flex-col gap-2">
          {/* Main Bubble */}
          <div className={`px-5 py-3.5 rounded-2xl shadow-sm border ${
            isUser 
              ? 'bg-blue-600 text-white border-blue-500 rounded-tr-none text-[15px]' 
              : 'bg-white text-slate-800 border-slate-100 rounded-tl-none text-[15px]'
          }`}>
            {isUser ? (
              <p className="whitespace-pre-wrap leading-relaxed">{content}</p>
            ) : (
              <div className="flex flex-col gap-3">
                {/* Confidence Pill Badge */}
                {confidence !== undefined && (
                  <div className="flex items-center gap-1.5 self-start">
                    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                      isLowConfidence
                        ? 'bg-rose-50 text-rose-700 border-rose-200/50'
                        : 'bg-emerald-50 text-emerald-700 border-emerald-200/50'
                    }`}>
                      {isLowConfidence ? <ShieldAlert size={10} /> : <CheckCircle2 size={10} />}
                      {((confidence || 0) * 100).toFixed(0)}% Confidence
                    </span>
                    
                    {supported === false && (
                      <span className="text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200/50 px-2 py-0.5 rounded-full inline-flex items-center gap-1">
                        <ShieldAlert size={10} /> Ungrounded Response
                      </span>
                    )}
                  </div>
                )}

                {/* Markdown text */}
                <div className="prose prose-sm prose-slate max-w-none leading-relaxed text-slate-800">
                  <ReactMarkdown>{content}</ReactMarkdown>
                </div>

                {/* Hallucination warning */}
                {isHallucinatedAlert && (
                  <div className="mt-1 flex items-start gap-2 p-3 rounded-xl bg-amber-50 border border-amber-200/60 text-xs text-amber-800 leading-relaxed font-medium">
                    <ShieldAlert className="shrink-0 text-amber-600 mt-0.5" size={15} />
                    <div>
                      <strong className="font-bold">Hallucination Warning:</strong> High risk of unsupported facts detected by evaluation agent (Score: {hallucination_score?.toFixed(2)}).
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sources and Feedback Bar (Assistant only) */}
          {!isUser && (
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 px-1 mt-1 text-[11px] text-slate-400">
              {/* Sources */}
              {sources && sources.length > 0 ? (
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-bold text-slate-400 mr-0.5 inline-flex items-center gap-1">
                    <FileText size={12} /> Sources:
                  </span>
                  {sources.slice(0, 3).map((src, sIdx) => (
                    <span 
                      key={sIdx}
                      className="px-2 py-0.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 border border-slate-200/40 cursor-help transition truncate max-w-[130px] font-medium"
                      title={src.text_snippet || 'Document source snippet'}
                    >
                      {src.source_name || 'Literature Doc'}
                    </span>
                  ))}
                  {sources.length > 3 && (
                    <span className="text-[10px] text-slate-400 font-semibold">
                      +{sources.length - 3} more
                    </span>
                  )}
                </div>
              ) : (
                <span className="italic text-slate-300">No source documents cited.</span>
              )}

              {/* Feedback Rating controls */}
              {interaction_id && (
                <div className="flex items-center gap-2 self-end md:self-auto font-semibold">
                  <span className="text-[10px] text-slate-400">Was this helpful?</span>
                  
                  {/* Helpful */}
                  <button
                    onClick={() => handleRating('helpful')}
                    disabled={ratingSubmitted}
                    className={`p-1.5 rounded-lg border transition ${
                      rating === 'helpful'
                        ? 'bg-emerald-50 text-emerald-600 border-emerald-200'
                        : 'border-slate-200/60 hover:bg-slate-100/80 text-slate-400 hover:text-slate-600'
                    }`}
                    title="Mark Helpful"
                  >
                    <ThumbsUp size={12} />
                  </button>

                  {/* Inaccurate */}
                  <button
                    onClick={() => handleRating('inaccurate')}
                    disabled={ratingSubmitted}
                    className={`p-1.5 rounded-lg border transition ${
                      rating === 'inaccurate'
                        ? 'bg-amber-50 text-amber-600 border-amber-200'
                        : 'border-slate-200/60 hover:bg-slate-100/80 text-slate-400 hover:text-slate-600'
                    }`}
                    title="Mark Inaccurate"
                  >
                    <ThumbsDown size={12} />
                  </button>

                  {/* Hallucinated */}
                  <button
                    onClick={() => handleRating('hallucinated')}
                    disabled={ratingSubmitted}
                    className={`p-1.5 rounded-lg border transition ${
                      rating === 'hallucinated'
                        ? 'bg-rose-50 text-rose-600 border-rose-200'
                        : 'border-slate-200/60 hover:bg-slate-100/80 text-slate-400 hover:text-slate-600'
                    }`}
                    title="Report Hallucination"
                  >
                    <ShieldAlert size={12} />
                  </button>

                  {ratingSubmitted && (
                    <span className="text-[9px] text-teal-600 font-bold bg-teal-50 px-1.5 py-0.5 rounded border border-teal-100/40 animate-pulse">
                      Vote Saved
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
