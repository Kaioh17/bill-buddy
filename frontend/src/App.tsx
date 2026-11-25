import { Route, Routes } from 'react-router'
import AppShell from './components/AppShell'
import Shell from './components/Shell'
import { GuestOnly, RequireAuth } from './lib/auth'
import AssumedList from './pages/AssumedList'
import ComingSoon from './pages/ComingSoon'
import Dashboard from './pages/Dashboard'
import Landing from './pages/Landing'
import Login from './pages/Login'
import NotFound from './pages/NotFound'
import Signup from './pages/Signup'
import Subscriptions from './pages/Subscriptions'

export default function App() {
  return (
    <Routes>
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="subscriptions" element={<Subscriptions />} />
          <Route path="subscriptions/assumed" element={<AssumedList />} />
          <Route path="subscriptions/new" element={<ComingSoon title="Manual Subscription" />} />
          <Route path="payments" element={<ComingSoon title="Payment Schedule" />} />
          <Route path="help" element={<ComingSoon title="Help" />} />
        </Route>
      </Route>
      <Route element={<Shell />}>
        <Route element={<GuestOnly />}>
          <Route index element={<Landing />} />
          <Route path="login" element={<Login />} />
          <Route path="signup" element={<Signup />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
