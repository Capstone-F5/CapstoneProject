import { useState, useEffect } from 'react'
import { fetchMenuData } from '../services/menuService'

export function useMenuData() {
  const [menuData,  setMenuData]  = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error,     setError]     = useState(null)

  useEffect(() => {
    let cancelled = false
    fetchMenuData()
      .then(data  => { if (!cancelled) { setMenuData(data);  setIsLoading(false) } })
      .catch(err  => { if (!cancelled) { setError(err);      setIsLoading(false) } })
    return () => { cancelled = true }
  }, [])

  const retry = () => {
    setIsLoading(true)
    setError(null)
    fetchMenuData()
      .then(data => { setMenuData(data);  setIsLoading(false) })
      .catch(err => { setError(err);      setIsLoading(false) })
  }

  return { menuData, isLoading, error, retry }
}
