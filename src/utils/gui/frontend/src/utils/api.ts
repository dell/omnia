// Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// --- Types ---
export interface JobStatus {
  jobId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  [key: string]: unknown;
}

class HTTPError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public response: Response
  ) {
    super(`HTTP ${status}: ${statusText}`);
    this.name = 'HTTPError';
    Object.setPrototypeOf(this, HTTPError.prototype);
  }
}

// --- Base fetcher ---
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const JSON_HEADERS = { 'Content-Type': 'application/json' } as const;
const DEFAULT_TIMEOUT_MS = 30_000;

async function request<T = unknown>(
  url: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const timeoutSignal = AbortSignal.timeout(timeoutMs);

  // Combine caller signal (if any) with timeout signal
  const signal = init?.signal
    ? AbortSignal.any([init.signal, timeoutSignal])
    : timeoutSignal;

  try {
    const response = await fetch(url, {
      ...init,
      signal,
    });
    if (!response.ok) {
      throw new HTTPError(response.status, response.statusText, response);
    }

    let body: T;
    try {
      body = await response.json() as T;
    } catch {
      throw new Error(
        `Expected JSON response from ${url} but received unparseable body (status ${response.status})`
      );
    }
    return body;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new Error(`Request timed out after ${timeoutMs}ms: ${url}`);
    }
    throw error;
  }
}

function get<T = unknown>(path: string): Promise<T> {
  return request<T>(`${API_BASE_URL}${path}`);
}

function post<T = unknown>(path: string, data: unknown): Promise<T> {
  return request<T>(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}

// --- API surface ---
export const api = {
  config: {
    generateAll: (data: unknown) => post<JobStatus>('/config/generate-all', data),
    getJobStatus: (jobId: string) =>
      get<JobStatus>(`/config/generate-all/${encodeURIComponent(jobId)}`),
  },
  localRepo: {
    generate: (data: unknown) => post<JobStatus>('/local-repo/generate', data),
  },
};

export { get };
