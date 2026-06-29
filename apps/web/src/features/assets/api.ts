import { api } from "@/lib/api/client";
import type { AssetLibraryRoot } from "./types";

export async function fetchAssetLibrary(): Promise<AssetLibraryRoot> {
  const data = await api.get<{ library: AssetLibraryRoot }>("/asset-library");
  return data.library;
}

export async function batchAddAssets(input: {
  library_id: string;
  category_id: string;
  items: { url: string; name?: string }[];
}): Promise<AssetLibraryRoot> {
  const data = await api.post<{ library: AssetLibraryRoot }>("/asset-library/items/batch", input);
  return data.library;
}

export async function deleteAssets(ids: string[], library_id: string): Promise<AssetLibraryRoot> {
  const data = await api.post<{ library: AssetLibraryRoot }>("/asset-library/items/delete", {
    ids,
    library_id,
  });
  return data.library;
}

export async function createAssetLibrary(name: string): Promise<AssetLibraryRoot> {
  const data = await api.post<{ library: AssetLibraryRoot }>("/asset-library/libraries", { name });
  return data.library;
}
