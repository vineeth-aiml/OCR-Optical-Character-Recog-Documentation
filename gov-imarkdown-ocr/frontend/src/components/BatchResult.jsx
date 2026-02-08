import React, { useMemo, useState } from "react";
import { marked } from "marked";

function downloadText(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function BatchResult({ batch }) {
  const [tab, setTab] = useState("combined");

  const combinedHtml = useMemo(
    () => marked.parse(batch.combined_markdown || ""),
    [batch.combined_markdown]
  );

  return (
    <div className="card">
      <div className="row">
        <div className="cardTitle">Results</div>
        <div className="tabs">
          <button className={tab==="combined" ? "tab active" : "tab"} onClick={() => setTab("combined")}>
            Combined Markdown
          </button>
          <button className={tab==="items" ? "tab active" : "tab"} onClick={() => setTab("items")}>
            Items ({batch.count})
          </button>
        </div>
      </div>

      <div className="actions">
        <button className="btnSmall" onClick={() => downloadText(`combined.md`, batch.combined_markdown || "")}>
          Download combined.md
        </button>
        <button className="btnSmall" onClick={() => downloadText(`batch.json`, JSON.stringify(batch, null, 2))}>
          Download batch.json
        </button>
      </div>

      {tab === "combined" && (
        <div className="markdownBox" dangerouslySetInnerHTML={{ __html: combinedHtml }} />
      )}

      {tab === "items" && (
        <div className="list">
          {batch.items.map((it) => (
            <div className="item" key={it.id}>
              <div><b>{it.filename}</b> <span className="pill">{it.type}</span></div>
              {it.type === "image" && it.result && (
                <div className="meta">
                  <div><b>doc_type:</b> {it.result.doc_type}</div>
                  <div><b>confidence:</b> {it.result.avg_confidence}</div>
                  <div><b>accepted:</b> {String(it.result.accepted)}</div>
                </div>
              )}
              {it.type === "pdf" && (
                <div className="meta">
                  <div><b>pages:</b> {it.pages}</div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
