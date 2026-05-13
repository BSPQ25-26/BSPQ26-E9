import { createI18n } from 'vue-i18n'
import en from './locales/en'
import es from './locales/es'

const LANG_KEY = 'wallabot_lang'

const getInitialLocale = () => {
  try {
    return localStorage.getItem(LANG_KEY) || 'en'
  } catch {
    return 'en'
  }
}

export const i18n = createI18n({
  legacy: false,
  locale: getInitialLocale(),
  fallbackLocale: 'en',
  messages: { en, es },
})

export const setLocale = (lang) => {
  i18n.global.locale.value = lang
  try {
    localStorage.setItem(LANG_KEY, lang)
  } catch {
    // ignore
  }
  document.documentElement.setAttribute('lang', lang)
}
