// ChatInterface.jsx
// The main Q&A panel. Shows the conversation history, handles sending
// questions to the backend, and displays sources + confidence for each answer.

import React, { useState, useRef, useEffect } from 'react';
import ConfidenceBar from './ConfidenceBar';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function SourcesList({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources-section" style={{ marginTop: '10px' }}>
      <h4>Source Clauses Used</h4>
      {sources.map((src, i) => (
        <div className="source-item" key={i}>
          <span className="clause-tag">{src.clause_number}</span>
          <span className="page-tag">Page {src.page_number}</span>
          <p className="source-text">{src.text_preview}...</p>
        </div>
      ))}
    </div>
  );
}

function ChatInterface({ docLoaded, suggestedQuestions }) {
  const [messages, setMessages] = useState([]);
  const [inputVal, setInputVal] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatBoxRef = useRef(null);

  // Auto-scroll to bottom when new messages come in
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  function fillQuestion(q) {
    setInputVal(q);
  }

  async function sendQuestion() {
    const question = inputVal.trim();
    if (!question || isLoading) return;

    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', text: question }]);
    setInputVal('');
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Something went wrong.');
      }

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: data.answer,
          confidence: data.confidence,
          sources: data.sources,
        },
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', text: `Error: ${err.message}`, isError: true },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendQuestion();
    }
  }

  return (
    <div>
      {/* Suggested questions */}
      {suggestedQuestions && suggestedQuestions.length > 0 && (
        <div className="card suggested-questions">
          <h3>Suggested Questions</h3>
          {suggestedQuestions.map((q, i) => (
            <div
              className="sq-item"
              key={i}
              onClick={() => fillQuestion(q)}
              title="Click to use this question"
            >
              {q}
            </div>
          ))}
        </div>
      )}

      {/* Chat box */}
      <div className="card" style={{ padding: '14px' }}>
        <div className="chat-box" ref={chatBoxRef}>
          {messages.length === 0 ? (
            <div className="empty-state">
              {docLoaded
                ? 'Ask anything about your document above ↑'
                : 'Upload a document first to start asking questions'}
            </div>
          ) : (
            messages.map((msg, i) => (
              <div className={`message ${msg.role}`} key={i}>
                <div className="message-label">
                  {msg.role === 'user' ? 'You' : 'Assistant'}
                </div>
                <div className="bubble">{msg.text}</div>
                {msg.role === 'assistant' && msg.confidence && (
                  <div style={{ marginTop: '6px', marginRight: '40px' }}>
                    <ConfidenceBar confidence={msg.confidence} />
                  </div>
                )}
                {msg.role === 'assistant' && msg.sources && (
                  <div style={{ marginRight: '40px' }}>
                    <SourcesList sources={msg.sources} />
                  </div>
                )}
              </div>
            ))
          )}

          {isLoading && (
            <div className="message assistant">
              <div className="message-label">Assistant</div>
              <div className="bubble" style={{ color: '#999' }}>
                <span className="spinner" style={{ borderTopColor: '#999', borderColor: '#ddd' }} />
                Searching document...
              </div>
            </div>
          )}
        </div>

        <div className="chat-input-row">
          <input
            id="chat-question-input"
            type="text"
            placeholder={docLoaded ? 'Ask a question about the document...' : 'Upload a document first'}
            value={inputVal}
            onChange={e => setInputVal(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!docLoaded || isLoading}
          />
          <button
            id="chat-send-btn"
            onClick={sendQuestion}
            disabled={!docLoaded || isLoading || !inputVal.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatInterface;
