const API_BASE = (import.meta.env.VITE_API_BASE ?? "/api").replace(/\/$/, "");

export async function uploadLocalAssets(files: File[], folder = ""): Promise<{ files: { url: string; name: string }[] }> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  if (folder) form.append("folder", folder);

  const response = await fetch(`${API_BASE}/local-assets/upload`, {
    method: "POST",
    body: form,
  });

  const text = await response.text();
  const parsed = text ? JSON.parse(text) : undefined;
  if (!response.ok) {
    throw new Error(typeof parsed?.detail === "string" ? parsed.detail : `上传失败 (${response.status})`);
  }
  return parsed as { files: { url: string; name: string }[] };
}
