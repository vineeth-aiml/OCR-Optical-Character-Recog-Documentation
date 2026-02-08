import React, { useRef } from "react";

export default function UploadPanel({ onUpload, busy }) {
  const ref = useRef(null);

  return (
    <div className="card">
      <input
        ref={ref}
        type="file"
        accept="image/*,application/pdf"
        multiple
        style={{ display: "none" }}
        onChange={(e) => {
          const files = Array.from(e.target.files || []);
          if (files.length) onUpload(files);
        }}
      />
      <button className="btn" disabled={busy} onClick={() => ref.current?.click()}>
        {busy ? "Processing..." : "Upload Images / PDFs"}
      </button>
      <div className="hint">Supports: JPG/PNG/TIFF/WEBP + PDF (multi-page, offline)</div>
    </div>
  );
}
