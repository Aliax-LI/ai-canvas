export interface ApiClientOptions {
  baseUrl?: string;
  fetch?: typeof fetch;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ApiClient {
  get<T>(path: string, init?: RequestInit): Promise<T>;
  post<T>(path: string, body?: unknown, init?: RequestInit): Promise<T>;
  put<T>(path: string, body?: unknown, init?: RequestInit): Promise<T>;
  delete<T>(path: string, init?: RequestInit): Promise<T>;
}

function resolveBaseUrl(explicit?: string): string {
  if (explicit) return explicit.replace(/\/$/, "");
  return "/api";
}

export function createApiClient(options: ApiClientOptions = {}): ApiClient {
  const baseUrl = resolveBaseUrl(options.baseUrl);
  const fetchFn = options.fetch ?? fetch;

  async function request<T>(
    method: string,
    path: string,
    body?: unknown,
    init?: RequestInit,
  ): Promise<T> {
    const url = path.startsWith("http") ? path : `${baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    const headers = new Headers(init?.headers);
    if (body !== undefined && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetchFn(url, {
      ...init,
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : init?.body,
    });

    const text = await response.text();
    const parsed: unknown = text ? JSON.parse(text) : undefined;

    if (!response.ok) {
      throw new ApiError(
        `API ${method} ${path} failed with ${response.status}`,
        response.status,
        parsed,
      );
    }

    return parsed as T;
  }

  return {
    get: (path, init) => request("GET", path, undefined, init),
    post: (path, body, init) => request("POST", path, body, init),
    put: (path, body, init) => request("PUT", path, body, init),
    delete: (path, init) => request("DELETE", path, undefined, init),
  };
}
