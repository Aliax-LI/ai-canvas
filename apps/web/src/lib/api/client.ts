import { createApiClient, type ApiClient } from "@infinite-canvas/api-types/client";
import { getApiBase } from "./base";

let cachedClient: ApiClient | null = null;
let cachedBase = "";

function getApi(): ApiClient {
  const base = getApiBase();
  if (!cachedClient || base !== cachedBase) {
    cachedClient = createApiClient({ baseUrl: base });
    cachedBase = base;
  }
  return cachedClient;
}

export const api: ApiClient = {
  get: (path, init) => getApi().get(path, init),
  post: (path, body, init) => getApi().post(path, body, init),
  put: (path, body, init) => getApi().put(path, body, init),
  delete: (path, init) => getApi().delete(path, init),
};
