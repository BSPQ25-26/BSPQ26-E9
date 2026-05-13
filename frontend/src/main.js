import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { pinia } from './stores'
import { i18n } from './i18n'
import './style.css'

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(i18n)

window.addEventListener('wallabot:auth-required', (event) => {
  const currentRoute = router.currentRoute.value

  if (currentRoute.path === '/login') {
    return
  }

  const redirectTarget = currentRoute.meta.publicOnly
    ? '/products'
    : currentRoute.fullPath || event.detail?.redirect || '/products'

  router.replace({
    path: '/login',
    query: {
      redirect: redirectTarget,
    },
  })
})

app.mount('#app')
