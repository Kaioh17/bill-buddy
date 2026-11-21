import { Route, Routes } from 'react-router'
import Shell from './components/Shell'
import { GuestOnly, RequireAuth } from './lib/auth'
import Dashboard from './pages/Dashboard'
import Landing from './pages/Landing'
import Login from './pages/Login'
import NotFound from './pages/NotFound'
import Signup from './pages/Signup'

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route element={<GuestOnly />}>
          <Route index element={<Landing />} />
          <Route path="login" element={<Login />} />
          <Route path="signup" element={<Signup />} />
        </Route>
        <Route element={<RequireAuth />}>
          <Route path="dashboard" element={<Dashboard />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
