import { AuthResponse, AuthUser } from "@/types/api";


const configuredBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
const API_BASE_URL = configuredBaseUrl || "";
const AUTH_USER_KEY = "researchmind.auth.user";
const AUTH_TOKEN_KEY = "researchmind.auth.token";
const DEMO_EMAIL = "demo@researchmind.ai";
const DEMO_PASSWORD = "researchmind-demo";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function emitAuthChange() {
  window.dispatchEvent(new Event("researchmind-auth-change"));
}

function storeSession(payload: AuthResponse): AuthUser {
  window.localStorage.setItem(AUTH_TOKEN_KEY, payload.access_token);
  window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(payload.user));
  emitAuthChange();
  return payload.user;
}

async function parseAuthError(response: Response): Promise<Error> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return new Error(payload.detail || `Authentication failed with status ${response.status}.`);
  } catch {
    return new Error(`Authentication failed with status ${response.status}.`);
  }
}

async function authRequest(path: string, body?: Record<string, string>, token?: string): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: body ? "POST" : "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!response.ok) {
    throw await parseAuthError(response);
  }
  return response.json();
}

function parseAuthUser(payload: unknown): AuthUser {
  if (!payload || typeof payload !== "object") {
    throw new Error("Malformed user response from backend.");
  }
  const item = payload as Partial<AuthUser>;
  if (typeof item.id !== "number" || typeof item.email !== "string" || typeof item.name !== "string") {
    throw new Error("Malformed user response from backend.");
  }
  return {
    id: item.id,
    name: item.name,
    email: item.email,
    created_at: typeof item.created_at === "string" ? item.created_at : "",
  };
}

function parseAuthResponse(payload: unknown): AuthResponse {
  if (!payload || typeof payload !== "object") {
    throw new Error("Malformed auth response from backend.");
  }
  const item = payload as Partial<AuthResponse>;
  if (typeof item.access_token !== "string" || !item.user) {
    throw new Error("Malformed auth response from backend.");
  }
  return {
    access_token: item.access_token,
    token_type: "bearer",
    user: parseAuthUser(item.user),
  };
}

export function getAuthToken(): string | null {
  if (!canUseStorage()) {
    return null;
  }
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

export function getCurrentUser(): AuthUser | null {
  if (!canUseStorage()) {
    return null;
  }
  const rawUser = window.localStorage.getItem(AUTH_USER_KEY);
  if (!rawUser) {
    return null;
  }
  try {
    return parseAuthUser(JSON.parse(rawUser));
  } catch {
    logout();
    return null;
  }
}

export function isAuthenticated(): boolean {
  return Boolean(getAuthToken() && getCurrentUser());
}

export async function loadCurrentUser(): Promise<AuthUser | null> {
  const token = getAuthToken();
  if (!token) {
    return null;
  }
  try {
    const user = parseAuthUser(await authRequest("/auth/me", undefined, token));
    window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
    emitAuthChange();
    return user;
  } catch (error) {
    logout();
    throw error;
  }
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const response = parseAuthResponse(await authRequest("/auth/login", { email: email.trim(), password }));
  return storeSession(response);
}

export async function loginWithDemoAccount(): Promise<AuthUser> {
  return login(DEMO_EMAIL, DEMO_PASSWORD);
}

export async function signup(name: string, email: string, password: string, confirmPassword: string): Promise<AuthUser> {
  if (password !== confirmPassword) {
    throw new Error("Passwords do not match.");
  }
  const response = parseAuthResponse(
    await authRequest("/auth/signup", {
      name: name.trim(),
      email: email.trim(),
      password,
    }),
  );
  return storeSession(response);
}

export function logout(): void {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
  window.localStorage.removeItem(AUTH_USER_KEY);
  emitAuthChange();
}
