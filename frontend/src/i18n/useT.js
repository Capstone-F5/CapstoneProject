import { useLocale } from './LocaleContext'
import translations from './translations'

export default function useT() {
  const { locale } = useLocale()
  const dict = translations[locale] ?? translations.ko
  return (key, ...args) => {
    const val = dict[key] ?? translations.ko[key] ?? key
    return typeof val === 'function' ? val(...args) : val
  }
}
