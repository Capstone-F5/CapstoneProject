import { useState, useEffect } from 'react'
import { useLocale } from '../i18n/LocaleContext'
import { fetchMenuData } from '../services/menuService'

export function useMenuData() {
  const { locale } = useLocale()
  const [menuData,  setMenuData]  = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error,     setError]     = useState(null)

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)
    fetchMenuData(locale)
      .then(data => { if (!cancelled) { setMenuData(data);  setIsLoading(false) } })
      .catch(err  => { if (!cancelled) { setError(err);      setIsLoading(false) } })
    return () => { cancelled = true }
  }, [locale]) // locale 변경 시 API 재호출 → 언어별 메뉴 이름 반영

  const retry = () => {
    setIsLoading(true)
    setError(null)
    fetchMenuData(locale)
      .then(data => { setMenuData(data);  setIsLoading(false) })
      .catch(err  => { setError(err);      setIsLoading(false) })
  }

  return { menuData, isLoading, error, retry }
}
