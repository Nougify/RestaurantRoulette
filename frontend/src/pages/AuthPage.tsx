import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'

import { login, register } from '../api/auth'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'

interface AuthPageProps {
  mode: 'login' | 'register'
}

const inputClass =
  'mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20'

/** The login and sign-up pages: the same form, posting to a different endpoint. */
export function AuthPage({ mode }: AuthPageProps) {
  const { token, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  // Where to go afterwards: the page that sent them here, or the home page.
  const from: string = location.state?.from ?? '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const submit = useMutation({
    mutationFn: mode === 'login' ? login : register,
    onSuccess: (session) => {
      signIn(session)
      navigate(from, { replace: true })
    },
  })

  if (token !== null && !submit.isSuccess) return <Navigate to={from} replace />

  function handleSubmit(event: FormEvent) {
    // Stop the browser's default full-page form submission; React handles it instead.
    event.preventDefault()
    submit.mutate({ email, password })
  }

  const error = submit.error instanceof ApiError ? submit.error : null
  const fieldError = (field: string) => error?.details.find((d) => d.field === field)?.message
  const isLogin = mode === 'login'

  return (
    <div className="flex h-full items-start justify-center overflow-y-auto p-6 pt-16">
      <form
        onSubmit={handleSubmit}
        noValidate
        className="w-full max-w-sm space-y-4 rounded-2xl border border-zinc-200 bg-white p-6"
      >
        <div>
          <h1 className="text-xl font-semibold">{isLogin ? 'Log in' : 'Create an account'}</h1>
          <p className="mt-1 text-sm text-zinc-500">
            {isLogin ? 'Welcome back.' : 'Save the places you want to remember.'}
          </p>
        </div>

        {error && error.details.length === 0 && (
          <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error.message}</p>
        )}

        <label className="block text-sm font-medium text-zinc-700">
          Email
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className={inputClass}
          />
          {fieldError('email') && (
            <span className="mt-1 block text-xs text-red-600">{fieldError('email')}</span>
          )}
        </label>

        <label className="block text-sm font-medium text-zinc-700">
          Password
          <input
            type="password"
            autoComplete={isLogin ? 'current-password' : 'new-password'}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={inputClass}
          />
          {!isLogin && !fieldError('password') && (
            <span className="mt-1 block text-xs text-zinc-500">
              At least 8 characters, including a number.
            </span>
          )}
          {fieldError('password') && (
            <span className="mt-1 block text-xs text-red-600">{fieldError('password')}</span>
          )}
        </label>

        <button
          type="submit"
          disabled={submit.isPending}
          className="w-full rounded-lg bg-accent py-2.5 text-sm font-semibold text-white hover:bg-accent-hover disabled:bg-zinc-300"
        >
          {submit.isPending ? 'Please wait…' : isLogin ? 'Log in' : 'Sign up'}
        </button>

        <p className="text-center text-sm text-zinc-500">
          {isLogin ? 'New here? ' : 'Already have an account? '}
          <Link
            to={isLogin ? '/register' : '/login'}
            state={{ from }}
            className="font-medium text-accent hover:text-accent-hover"
          >
            {isLogin ? 'Create an account' : 'Log in'}
          </Link>
        </p>
      </form>
    </div>
  )
}
