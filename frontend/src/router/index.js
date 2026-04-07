import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Pipeline',
    component: () => import('@/views/Pipeline.vue'),
    meta: { requiresAuth: true, role: 'teacher' }
  },
  {
    path: '/kgqa',
    name: 'KGQA',
    component: () => import('@/views/KGQA.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/students',
    name: 'Students',
    component: () => import('@/views/Students.vue'),
    meta: { requiresAuth: true, role: 'teacher' }
  },
  {
    path: '/student-home',
    name: 'StudentHome',
    component: () => import('@/views/StudentHome.vue'),
    meta: { requiresAuth: true, role: 'student' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  
  if (to.meta.requiresAuth && !token) {
    next('/login')
    return
  }

  if (to.path === '/login' && token) {
    if (user.role === 'teacher') {
      next('/')
    } else {
      next('/student-home')
    }
    return
  }

  if (to.meta.role && user.role !== to.meta.role) {
    if (user.role === 'teacher') {
      next('/')
    } else {
      next('/student-home')
    }
    return
  }

  next()
})

export default router
