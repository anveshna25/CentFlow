import { useState } from 'react'
import './App.css'
import { NavigationProvider, useNavigation } from './state/NavigationContext'
import { PAGES } from './state/pages'
import { AppLayout } from './layouts/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { MarketsPage } from './pages/MarketsPage'
import { WatchlistsPage } from './pages/WatchlistsPage'
import { PortfoliosPage } from './pages/PortfoliosPage'

function MainContent({ searchValue }) {
  const { activePage } = useNavigation()

  switch (activePage) {
    case PAGES.MARKETS:
      return <MarketsPage externalSearch={searchValue} />
    case PAGES.WATCHLISTS:
      return <WatchlistsPage />
    case PAGES.PORTFOLIOS:
      return <PortfoliosPage />
    case PAGES.DASHBOARD:
    default:
      return <DashboardPage />
  }
}

function App() {
  const [searchValue, setSearchValue] = useState('')

  return (
    <NavigationProvider>
      <AppLayout onSearch={setSearchValue} searchValue={searchValue}>
        <MainContent searchValue={searchValue} />
      </AppLayout>
    </NavigationProvider>
  )
}

export default App