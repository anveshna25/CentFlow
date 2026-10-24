import { createContext, useContext, useState, useEffect } from 'react'
import { PAGES } from './pages'

const NavigationContext = createContext({
  activePage: PAGES.DASHBOARD,
  navigate: () => {},
  pageParams: {},
})

export function NavigationProvider({ children }) {
  const getInitialPage = () => {
    const hash = window.location.hash.replace('#', '').toLowerCase()
    if (Object.values(PAGES).includes(hash)) {
      return hash
    }
    return PAGES.DASHBOARD
  }

  const [activePage, setActivePage] = useState(getInitialPage)
  const [pageParams, setPageParams] = useState({})

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '').toLowerCase()
      if (Object.values(PAGES).includes(hash)) {
        setActivePage(hash)
      }
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const navigate = (page, params = {}) => {
    if (Object.values(PAGES).includes(page)) {
      setActivePage(page)
      setPageParams(params)
      window.location.hash = page
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  return (
    <NavigationContext.Provider value={{ activePage, navigate, pageParams }}>
      {children}
    </NavigationContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useNavigation() {
  const context = useContext(NavigationContext)
  if (!context) {
    throw new Error('useNavigation must be used within a NavigationProvider')
  }
  return context
}
