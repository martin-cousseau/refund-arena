import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { Shell } from "@/components/layout/shell"
import { ArenaProvider } from "@/lib/arena-context"
import { OverviewPage } from "@/pages/overview-page"
import { PromptsPage } from "@/pages/prompts-page"
import { QueuePage } from "@/pages/queue-page"
import { RunsPage } from "@/pages/runs-page"
import { ShopPage } from "@/pages/shop-page"

export function App() {
  return (
    <ArenaProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<OverviewPage />} />
            <Route path="queue" element={<QueuePage />} />
            <Route path="queue/:ticketId" element={<QueuePage />} />
            <Route path="runs" element={<RunsPage />} />
            <Route path="prompts" element={<PromptsPage />} />
            <Route path="shop" element={<ShopPage />} />
            <Route path="scoreboard" element={<Navigate to="/runs" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ArenaProvider>
  )
}

export default App
