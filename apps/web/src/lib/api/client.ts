import { createApiClient } from "@infinite-canvas/api-types/client";

const baseUrl = import.meta.env.VITE_API_BASE ?? "/api";

export const api = createApiClient({ baseUrl });
