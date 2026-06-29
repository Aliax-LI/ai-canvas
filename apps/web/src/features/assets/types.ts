export interface AssetItem {
  id: string;
  name: string;
  url: string;
  kind?: string;
  classification?: string;
  created_at?: number;
}

export interface AssetCategory {
  id: string;
  name: string;
  type: string;
  items: AssetItem[];
}

export interface AssetLibrary {
  id: string;
  name: string;
  type: string;
  categories: AssetCategory[];
}

export interface AssetLibraryRoot {
  libraries: AssetLibrary[];
  active_library_id?: string;
}
