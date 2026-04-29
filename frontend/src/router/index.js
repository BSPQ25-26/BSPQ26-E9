import { createRouter, createWebHashHistory } from 'vue-router'
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/products',
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: {
        publicOnly: true,
      },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: {
        publicOnly: true,
      },
    },
    {
      path: '/auth/callback',
      name: 'social-auth-callback',
      component: () => import('@/views/SocialAuthCallbackView.vue'),
    },
    {
      path: '/products',
      name: 'products',
      component: () => import('@/views/ProductsView.vue'),
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/products/create',
      redirect: {
        name: 'product-create',
        params: {
          id: 'new',
        },
      },
    },
    {
      path: '/products/:id/create',
      name: 'product-create',
      component: () => import('@/views/ProductCreateView.vue'),
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/products/:id/edit',
      name: 'product-edit',
      component: () => import('@/views/ProductCreateView.vue'),
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/products/:id',
      name: 'product-detail',
      component: () => import('@/views/ProductDetailView.vue'),
      meta: {
        requiresAuth: true,
      },
    },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore(pinia)
  const token = authStore.syncTokenFromStorage()
  const isAuthenticated = Boolean(token)
  const requiresAuth = to.matched.some((route) => route.meta.requiresAuth)
  const publicOnly = to.matched.some((route) => route.meta.publicOnly)

  if (requiresAuth && !isAuthenticated) {
    return {
      path: '/login',
      query: {
        redirect: to.fullPath,
      },
    }
  }

  if (publicOnly && isAuthenticated) {
    return {
      path: '/products',
    }
  }

  return true
})

export default router
