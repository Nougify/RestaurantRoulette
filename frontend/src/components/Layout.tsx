import { Link, NavLink, Outlet } from 'react-router'

import { useAuth } from '../auth/AuthContext'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm font-medium ${isActive ? 'text-zinc-900' : 'text-zinc-500 hover:text-zinc-900'}`

/** The page frame: header on top, the current route's page below (rendered by <Outlet />). */
export function Layout() {
  const { user, isChecking, signOut } = useAuth()

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200 bg-white px-5">
        <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <img src={`${import.meta.env.BASE_URL}favicon.svg`} alt="" className="h-6 w-6" />
          RestaurantRoulette
        </Link>
        <nav className="flex items-center gap-5">
          <NavLink to="/favourites" className={navClass}>
            Favourites
          </NavLink>
          {isChecking ? null : user ? (
            <>
              <span className="hidden text-sm text-zinc-500 sm:inline">{user.email}</span>
              <button
                type="button"
                onClick={signOut}
                className="text-sm font-medium text-zinc-500 hover:text-zinc-900"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={navClass}>
                Log in
              </NavLink>
              <Link
                to="/register"
                className="rounded-lg bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-zinc-700"
              >
                Sign up
              </Link>
            </>
          )}
        </nav>
      </header>
      <main className="min-h-0 flex-1">
        <Outlet />
      </main>
    </div>
  )
}
