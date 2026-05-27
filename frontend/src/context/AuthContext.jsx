import { createContext, useContext, useState, useEffect } from 'react'
import { login as apiLogin, signup as apiSignup, fetchMe } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem('token')))

  useEffect(() => {
    let active = true
    const token = localStorage.getItem('token')
    if (!token) return undefined

    fetchMe()
      .then((me) => { if (active) setUser(me) })
      .catch(() => localStorage.removeItem('token'))
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [])

  async function login(email, password) {
    const { access_token } = await apiLogin(email, password)
    localStorage.setItem('token', access_token)
    const me = await fetchMe()
    setUser(me)
  }

  async function signup(email, password, name) {
    const { access_token } = await apiSignup(email, password, name)
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

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
