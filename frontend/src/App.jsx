import { useState } from 'react'
import './App.css'
import { ThemeProvider } from './state/ThemeContext'
import { NavigationProvider, useNavigation } from './state/NavigationContext'
import { PAGES } from './state/pages'
import { AppLayout } from './layouts/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { MarketsPage } from './pages/MarketsPage'
import { WatchlistsPage } from './pages/WatchlistsPage'
import { PortfoliosPage } from './pages/PortfoliosPage'
import { AssetDetailModal } from './components/market/AssetDetailModal'

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
  const [globalInspectingAsset, setGlobalInspectingAsset] = useState(null)

  return (
    <ThemeProvider>
      <NavigationProvider>
        <AppLayout
          onSearch={setSearchValue}
          searchValue={searchValue}
          onSelectAsset={(asset) => setGlobalInspectingAsset(asset)}
        >
          <MainContent searchValue={searchValue} />
        </AppLayout>

        {globalInspectingAsset && (
          <AssetDetailModal
            instrument={globalInspectingAsset}
            onClose={() => setGlobalInspectingAsset(null)}
          />
        )}
      </NavigationProvider>
    </ThemeProvider>
  )
}

export default App