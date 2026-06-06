// DocumentComparison.jsx
// Lets the user upload two PDFs and ask comparison questions across both.
// Uses /upload-compare and /compare endpoints.

import React, { useState, useRef } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function CompareUploadBox({ label, id, file, onFileSelect }) {
  const inputRef = useRef(null);

  function onDrop(e) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f && f.type === 'application/pdf') onFileSelect(f);
  }

  return (
    <div className="card">
      <h3>{label}</h3>
      <div
        className="upload-zone"
        style={{ padding: '18px 10px' }}
        onClick={() => inputRef.current.click()}
        onDrop={onDrop}
        onDragOver={e => e.preventDefault()}
      >
        <div className="upload-icon">📄</div>
        <p style={{ fontSize: '13px' }}>
          {file ? file.name : 'Click or drag PDF here'}
        </p>
        <input
          id={id}
          type="file"
          accept=".pdf"
          ref={inputRef}
          style={{ display: 'none' }}
          onChange={e => onFileSelect(e.target.files[0])}
        />
      </div>
    </div>
  );
}

function DocumentComparison() {
  const [fileA, setFileA] = useState(null);
  const [fileB, setFileB] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [docsReady, setDocsReady] = useState(false);

  async function handleCompareUpload() {
    if (!fileA || !fileB) return;
    setUploadStatus({ type: 'loading', msg: 'Indexing both documents...' });

    const formData = new FormData();
    formData.append('file_a', fileA);
    formData.append('file_b', fileB);

    try {
      const res = await fetch(`${API_BASE}/upload-compare`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed.');

      setUploadStatus({
        type: 'success',
        msg: `Doc A: ${data.doc_a.chunks} clauses | Doc B: ${data.doc_b.chunks} clauses`,
      });
      setDocsReady(true);
    } catch (err) {
      setUploadStatus({ type: 'error', msg: err.message });
    }
  }

  async function handleCompare() {
    if (!question.trim() || !docsReady) return;
    setIsLoading(true);
    setAnswer(null);

    try {
      const res = await fetch(`${API_BASE}/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Comparison failed.');
      setAnswer(data);
    } catch (err) {
      setAnswer({ error: err.message });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div>
      <div className="comparison-upload-row">
        <CompareUploadBox
          label="Document A"
          id="compare-file-a"
          file={fileA}
          onFileSelect={setFileA}
        />
        <CompareUploadBox
          label="Document B"
          id="compare-file-b"
          file={fileB}
          onFileSelect={setFileB}
        />
      </div>

      <button
        id="compare-upload-btn"
        className="upload-btn"
        style={{ marginBottom: '16px' }}
        onClick={handleCompareUpload}
        disabled={!fileA || !fileB || (uploadStatus && uploadStatus.type === 'loading')}
      >
        {uploadStatus && uploadStatus.type === 'loading' ? (
          <>
            <span className="spinner" />
            Indexing...
          </>
        ) : (
          'Index Both Documents'
        )}
      </button>

      {uploadStatus && (
        <div className={`status-msg ${uploadStatus.type}`} style={{ marginBottom: '16px' }}>
          {uploadStatus.msg}
        </div>
      )}

      {docsReady && (
        <div className="card">
          <h3>Comparison Question</h3>
          <p style={{ fontSize: '13px', color: '#777', marginBottom: '10px' }}>
            Example: "Which agreement has a longer notice period?" or "Which contract has a higher security deposit?"
          </p>
          <div className="chat-input-row" style={{ marginBottom: '12px' }}>
            <input
              id="compare-question-input"
              type="text"
              placeholder="Ask a comparison question..."
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCompare()}
            />
            <button
              id="compare-ask-btn"
              onClick={handleCompare}
              disabled={isLoading || !question.trim()}
            >
              Compare
            </button>
          </div>

          {isLoading && (
            <div className="status-msg loading">
              <span className="spinner" style={{ borderTopColor: '#7b5a00', borderColor: '#e0c97f' }} />
              Comparing documents...
            </div>
          )}

          {answer && !answer.error && (
            <div>
              <div style={{
                background: '#f5f7ff',
                border: '1px solid #d0d8ff',
                borderRadius: '6px',
                padding: '14px',
                marginBottom: '12px',
                fontSize: '14px',
                lineHeight: '1.6',
              }}>
                {answer.answer}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '600', color: '#555', marginBottom: '6px' }}>
                    DOC A — Sources
                  </div>
                  {answer.sources_a.map((src, i) => (
                    <div className="source-item" key={i}>
                      <span className="clause-tag">{src.clause_number}</span>
                      <p className="source-text" style={{ marginTop: '4px' }}>{src.text_preview}...</p>
                    </div>
                  ))}
                </div>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '600', color: '#555', marginBottom: '6px' }}>
                    DOC B — Sources
                  </div>
                  {answer.sources_b.map((src, i) => (
                    <div className="source-item" key={i} style={{ borderLeftColor: '#e67e22' }}>
                      <span className="clause-tag" style={{ background: '#fff3e0', color: '#e67e22' }}>
                        {src.clause_number}
                      </span>
                      <p className="source-text" style={{ marginTop: '4px' }}>{src.text_preview}...</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {answer && answer.error && (
            <div className="status-msg error">{answer.error}</div>
          )}
        </div>
      )}
    </div>
  );
}

export default DocumentComparison;
