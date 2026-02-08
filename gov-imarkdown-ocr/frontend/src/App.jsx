import React, { useState } from "react";
import UploadPanel from "./components/UploadPanel.jsx";
import BatchResult from "./components/BatchResult.jsx";
import { convertBatch } from "./api.js";

export default function App() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function onUpload(files) {
    setError("");
    setResult(null);
    setBusy(true);
    try {
      const r = await convertBatch(files);
      setResult(r);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container">
      <header className="header">
        <div className="title">Gov iMarkdown OCR (Offline)</div>
        <div className="subtitle">Images + PDFs → Clean Markdown + JSON (Tables + spans)</div>
      </header>

      <UploadPanel onUpload={onUpload} busy={busy} />

      {error && <div className="error">{error}</div>}

      {result && <BatchResult batch={result} />}
    </div>
  );
}
