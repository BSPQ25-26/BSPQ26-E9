import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { pinia } from './stores'
import './style.css'

const app = createApp(App)

app.use(pinia)
app.use(router)

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
