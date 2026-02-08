export async function convertBatch(files) {
  const fd = new FormData();
  for (const f of files) fd.append("files", f);

  const res = await fetch("/api/batch", { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

export async function convertSingle(file) {
  const fd = new FormData();
  fd.append("file", file);

  const res = await fetch("/api/convert", { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}
