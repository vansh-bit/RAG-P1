// App.jsx — root component
// Two tabs: "Analyze" (single doc QA) and "Compare" (two doc comparison)

import React, { useState } from 'react';
import './App.css';

import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';
import DocumentComparison from './components/DocumentComparison';

function App() {
  const [activeTab, setActiveTab] = useState('analyze');
  const [docInfo, setDocInfo] = useState(null); // { filename, chunkCount, suggestedQuestions }

  function handleUploadSuccess(info) {
    setDocInfo(info);
  }

  return (
    <div>
      {/* Header */}
      <header className="app-header">
        <div>
          <div style={{ fontSize: '22px' }}>⚖️</div>
        </div>
        <div>
          <h1>Legal Doc Analyzer</h1>
          <div className="subtitle">
            RAG-powered Q&amp;A for Indian rental agreements and legal contracts
          </div>
        </div>
      </header>

      {/* Tab bar */}
      <div className="tab-bar">
        <button
          id="tab-analyze"
          className={activeTab === 'analyze' ? 'active' : ''}
          onClick={() => setActiveTab('analyze')}
        >
          Analyze Document
        </button>
        <button
          id="tab-compare"
          className={activeTab === 'compare' ? 'active' : ''}
          onClick={() => setActiveTab('compare')}
        >
          Compare Documents
        </button>
      </div>

      {/* Main content */}
      {activeTab === 'analyze' && (
        <div className="main-layout">
          {/* Left: upload */}
          <div className="left-panel">
            <div className="card">
              <h3>Upload Document</h3>
              <FileUpload onUploadSuccess={handleUploadSuccess} />
              {docInfo && (
                <p className="chunk-count">
                  ✓ {docInfo.chunkCount} clauses indexed from {docInfo.filename}
                </p>
              )}
            </div>

            {/* How it works — brief explainer */}
            <div className="card">
              <h3>How it works</h3>
              <ol style={{ paddingLeft: '16px', fontSize: '13px', color: '#555', lineHeight: '1.8' }}>
                <li>Upload a PDF contract</li>
                <li>Document is split by clause structure</li>
                <li>Clauses are embedded with MiniLM</li>
                <li>Your question retrieves relevant clauses via MMR</li>
                <li>LLaMA 3 answers using only those clauses</li>
              </ol>
            </div>
          </div>

          {/* Right: chat */}
          <div className="right-panel">
            <ChatInterface
              docLoaded={docInfo !== null}
              suggestedQuestions={docInfo ? docInfo.suggestedQuestions : []}
            />
          </div>
        </div>
      )}

      {activeTab === 'compare' && (
        <div style={{ padding: '20px 24px', maxWidth: '1000px', margin: '0 auto' }}>
          <DocumentComparison />
        </div>
      )}
    </div>
  );
}

export default App;
