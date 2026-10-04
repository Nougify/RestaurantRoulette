import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { fetchCurrentUser } from '../api/auth'
import { ApiError } from '../api/client'
import type { Session, User } from '../api/types'

const TOKEN_KEY = 'restaurant-roulette.token'

interface AuthState {
  token: string | null
  user: User | null
  // True while a saved token is being checked with the server on page load.
  isChecking: boolean
  signIn: (session: Session) => void
  signOut: () => void
}

// Context lets any component read the auth state without passing it down through props.
const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  // Read once, on first render, so a signed-in visitor stays signed in after a reload.
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))

  // Ask the server who the token belongs to. The token is part of the key, so a new
  // token triggers a new request and the previous user's data is never reused.
  const me = useQuery({
    queryKey: ['me', token],
    queryFn: () => fetchCurrentUser(token!),
    enabled: token !== null,
    staleTime: Infinity,
    retry: false,
  })

  const signOut = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    queryClient.removeQueries({ queryKey: ['favourites'] })
  }, [queryClient])

  const signIn = useCallback(
    (session: Session) => {
      localStorage.setItem(TOKEN_KEY, session.token)
      // The login response already says who the user is; no need to ask again.
      queryClient.setQueryData(['me', session.token], session.user)
      setToken(session.token)
    },
    [queryClient],
  )

  // A saved token the server rejects (expired after 7 days, or the account is gone).
  useEffect(() => {
    if (me.error instanceof ApiError && me.error.status === 401) signOut()
  }, [me.error, signOut])

  const value = useMemo(
    () => ({
      token,
      user: me.data ?? null,
      isChecking: token !== null && me.isPending,
      signIn,
      signOut,
    }),
    [token, me.data, me.isPending, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const auth = useContext(AuthContext)
  if (auth === null) throw new Error('useAuth must be used inside <AuthProvider>')
  return auth
}
