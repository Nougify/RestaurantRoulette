import { apiFetch } from './client'
import type { Credentials, Session, User } from './types'

export function register(credentials: Credentials): Promise<Session> {
  return apiFetch<Session>('/api/auth/register', { method: 'POST', body: credentials })
}

export function login(credentials: Credentials): Promise<Session> {
  return apiFetch<Session>('/api/auth/login', { method: 'POST', body: credentials })
}

export async function fetchCurrentUser(token: string): Promise<User> {
  const data = await apiFetch<{ user: User }>('/api/auth/me', { token })
  return data.user
}
