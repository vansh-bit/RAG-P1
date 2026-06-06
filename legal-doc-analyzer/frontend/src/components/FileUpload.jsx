// FileUpload.jsx
// Handles PDF file selection (click or drag & drop) and calls the
// /upload endpoint. On success, passes suggested questions up to App.

import React, { useState, useRef } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function FileUpload({ onUploadSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState(null); // { type: 'success'|'error'|'loading', msg }
  const fileInputRef = useRef(null);

  function handleFileChange(file) {
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
      setStatus(null);
    } else {
      setStatus({ type: 'error', msg: 'Please select a PDF file.' });
    }
  }

  function onInputChange(e) {
    handleFileChange(e.target.files[0]);
  }

  function onDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    handleFileChange(e.dataTransfer.files[0]);
  }

  function onDragOver(e) {
    e.preventDefault();
    setIsDragging(true);
  }

  function onDragLeave() {
    setIsDragging(false);
  }

  async function handleUpload() {
    if (!selectedFile) return;

    setStatus({ type: 'loading', msg: 'Uploading and indexing document...' });

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed.');
      }

      setStatus({
        type: 'success',
        msg: `Indexed ${data.chunk_count} clauses from "${data.filename}"`,
      });

      onUploadSuccess({
        filename: data.filename,
        chunkCount: data.chunk_count,
        suggestedQuestions: data.suggested_questions || [],
      });
    } catch (err) {
      setStatus({ type: 'error', msg: err.message });
    }
  }

  return (
    <div>
      <div
        className={`upload-zone ${isDragging ? 'dragging' : ''}`}
        onClick={() => fileInputRef.current.click()}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
      >
        <div className="upload-icon">📄</div>
        <p>Click to select or drag & drop a PDF</p>
        <p className="small">Supports rental agreements, contracts, legal documents</p>
        <input
          id="pdf-file-input"
          type="file"
          accept=".pdf"
          ref={fileInputRef}
          onChange={onInputChange}
        />
      </div>

      {selectedFile && (
        <div className="uploaded-file">
          <span>📎</span>
          <span className="file-name">{selectedFile.name}</span>
          <span style={{ color: '#888', fontSize: '12px' }}>
            {(selectedFile.size / 1024).toFixed(0)} KB
          </span>
        </div>
      )}

      <button
        id="upload-submit-btn"
        className="upload-btn"
        onClick={handleUpload}
        disabled={!selectedFile || (status && status.type === 'loading')}
      >
        {status && status.type === 'loading' ? (
          <>
            <span className="spinner" />
            Processing...
          </>
        ) : (
          'Upload & Analyze'
        )}
      </button>

      {status && (
        <div className={`status-msg ${status.type}`}>{status.msg}</div>
      )}
    </div>
  );
}

export default FileUpload;
