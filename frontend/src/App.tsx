import { Navigate, Route, Routes } from 'react-router'

import { Layout } from './components/Layout'
import { AuthPage } from './pages/AuthPage'
import { FavouritesPage } from './pages/FavouritesPage'
import { HomePage } from './pages/HomePage'

/** URL → page. Every page is drawn inside <Layout>, which provides the header. */
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="login" element={<AuthPage mode="login" />} />
        <Route path="register" element={<AuthPage mode="register" />} />
        <Route path="favourites" element={<FavouritesPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
