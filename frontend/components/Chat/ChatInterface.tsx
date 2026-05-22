'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { ChatMessage, ChatMessageProps } from './ChatMessage';
import { api } from '../../services/api';

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessageProps[]>([
    {
      role: 'assistant',
      content: 'Hello! I am your GraphRAG Medical Research Assistant. How can I help you today?'
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    setInput('');
    
    // Add user message to UI
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsLoading(true);

    try {
      // Call backend API
      const response = await api.query({ query: userMsg });
      
      // Add AI response to UI
      setMessages(prev => [...prev, { role: 'assistant', content: response.answer }]);
    } catch (error: any) {
      console.error('Failed to send message:', error);
      
      let errorMessage = 'Sorry, I encountered an error communicating with the backend.';
      if (error?.response?.data?.detail) {
        errorMessage = `Backend Error: ${error.response.data.detail}`;
      } else if (error?.message) {
        errorMessage = `Network Error: ${error.message}`;
      }

      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: errorMessage 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center shadow-sm z-10">
        <h1 className="text-xl font-semibold text-slate-800 flex items-center gap-2">
          <span className="text-teal-600">GraphRAG</span> Medical Assistant
        </h1>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
        <div className="max-w-4xl mx-auto">
          {messages.map((msg, idx) => (
            <ChatMessage key={idx} role={msg.role} content={msg.content} />
          ))}
          
          {isLoading && (
            <div className="flex items-center gap-3 text-slate-400 mb-6 px-4">
              <Loader2 className="animate-spin" size={20} />
              <span className="text-sm font-medium animate-pulse">Researching medical graphs...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-slate-200 p-4">
        <div className="max-w-4xl mx-auto relative">
          <form onSubmit={handleSubmit} className="relative flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a medical research question..."
              className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3 pl-4 pr-12 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500 resize-none max-h-32 shadow-sm text-[15px]"
              rows={1}
              style={{ minHeight: '52px' }}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="absolute right-2 bottom-2 p-2 rounded-xl bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-50 disabled:hover:bg-teal-600 transition-colors shadow-sm"
            >
              <Send size={18} />
            </button>
          </form>
          <div className="text-center mt-2">
            <span className="text-[11px] text-slate-400">AI can make mistakes. Verify medical information.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
