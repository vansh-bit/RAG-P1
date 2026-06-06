// ConfidenceBar.jsx
// Shows a visual low/medium/high confidence indicator based on
// the retrieval similarity score returned by the backend.

import React from 'react';

function ConfidenceBar({ confidence }) {
  if (!confidence) return null;

  const { label, score } = confidence;

  // Map score (0–1) to a percentage width for the bar
  const fillPercent = Math.round(score * 100);

  return (
    <div className="confidence-row">
      <span className={`confidence-label ${label}`}>{label}</span>
      <div className="confidence-bar-track">
        <div
          className={`confidence-bar-fill ${label}`}
          style={{ width: `${fillPercent}%` }}
        />
      </div>
      <span className="confidence-score">{score}</span>
    </div>
  );
}

export default ConfidenceBar;
