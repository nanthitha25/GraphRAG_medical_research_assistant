import React from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Bot } from 'lucide-react';

export interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
}

export function ChatMessage({ role, content }: ChatMessageProps) {
  const isUser = role === 'user';

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      <div className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start gap-4`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-blue-600 text-white' : 'bg-teal-600 text-white'
        }`}>
          {isUser ? <User size={18} /> : <Bot size={18} />}
        </div>

        {/* Message Bubble */}
        <div className={`px-5 py-3 rounded-2xl shadow-sm ${
          isUser 
            ? 'bg-blue-500 text-white rounded-tr-none' 
            : 'bg-white text-slate-800 border border-slate-100 rounded-tl-none'
        }`}>
          {isUser ? (
            <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{content}</p>
          ) : (
            <div className="prose prose-sm prose-slate max-w-none">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
