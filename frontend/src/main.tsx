import 'leaflet/dist/leaflet.css'
import './index.css'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'

import App from './App.tsx'
import { AuthProvider } from './auth/AuthContext'

// One cache for all server data in the app.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      // Restaurant data barely changes, so switching browser tabs need not refetch it.
      refetchOnWindowFocus: false,
    },
  },
})

// Providers wrap the app so every component can reach the router, the query cache and
// the auth state. AuthProvider uses the query cache, so it must sit inside it.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  </StrictMode>,
)
