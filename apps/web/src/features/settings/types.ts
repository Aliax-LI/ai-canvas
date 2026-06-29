/** API provider — mirrors backend public_provider + save payload fields. */

export interface ApiProvider {
  id: string;
  name: string;
  base_url: string;
  protocol: string;
  image_request_mode: string;
  image_generation_endpoint?: string;
  image_edit_endpoint?: string;
  enabled: boolean;
  primary: boolean;
  image_models: string[];
  chat_models: string[];
  video_models: string[];
  model_protocols?: Record<string, string>;
  ms_loras?: Record<string, unknown>[];
  rh_apps?: Record<string, unknown>[];
  rh_workflows?: Record<string, unknown>[];
  volcengine_project_name?: string;
  volcengine_region?: string;
  has_key?: boolean;
  key_preview?: string;
  has_wallet_key?: boolean;
  wallet_key_preview?: string;
  has_volcengine_access_key?: boolean;
  volcengine_access_key_preview?: string;
  has_volcengine_secret_key?: boolean;
  volcengine_secret_key_preview?: string;
}

export interface SaveProviderPayload extends ApiProvider {
  api_key?: string | null;
  wallet_api_key?: string | null;
  volcengine_access_key_id?: string | null;
  volcengine_secret_access_key?: string | null;
  clear_key?: boolean;
  clear_wallet_key?: boolean;
  clear_volcengine_access_key_id?: boolean;
  clear_volcengine_secret_access_key?: boolean;
}

export interface TestConnectionPayload {
  base_url: string;
  api_key: string;
  provider_id: string;
  protocol: string;
  image_request_mode: string;
}

export interface WorkflowSummary {
  name: string;
  title: string;
  builtin: boolean;
  field_count?: number;
}

export interface WorkflowField {
  id: string;
  node: string;
  input: string;
  name: string;
  type: string;
  default?: unknown;
  min?: number | null;
  max?: number | null;
  step?: number | null;
  options?: string[];
  random_enabled?: boolean;
}

export interface WorkflowConfig {
  title: string;
  fields: WorkflowField[];
  mini_cards?: Record<string, unknown>;
}

export interface WorkflowDetail {
  name: string;
  workflow: Record<string, unknown>;
  config: WorkflowConfig;
  builtin?: boolean;
}
