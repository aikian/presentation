import { createContext, useContext, useState, useEffect } from 'react'
import { login as apiLogin, signup as apiSignup, fetchMe } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { setLoading(false); return }
    fetchMe()
      .then(setUser)
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false))
  }, [])

  async function login(email, password) {
    const { access_token } = await apiLogin(email, password)
    localStorage.setItem('token', access_token)
    const me = await fetchMe()
    setUser(me)
  }

  async function signup(email, password) {
    const { access_token } = await apiSignup(email, password)
    localStorage.setItem('token', access_token)
    const me = await fetchMe()
    setUser(me)
  }

  function logout() {
    localStorage.removeItem('token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
