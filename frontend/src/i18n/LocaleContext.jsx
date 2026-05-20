import { createContext, useContext, useState } from 'react'

const LocaleContext = createContext({ locale: 'ko', setLocale: () => {} })

export function LocaleProvider({ children }) {
  const [locale, setLocale] = useState('ko')
  return (
    <LocaleContext.Provider value={{ locale, setLocale }}>
      {children}
    </LocaleContext.Provider>
  )
}

export function useLocale() {
  return useContext(LocaleContext)
}
