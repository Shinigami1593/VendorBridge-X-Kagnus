import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../stores/auth'
import AppLayout from '../components/AppLayout.vue'
import ComingSoon from '../views/ComingSoon.vue'
import DashboardView from '../views/DashboardView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import LoginView from '../views/LoginView.vue'
import NoAccessView from '../views/NoAccessView.vue'
import RegisterView from '../views/RegisterView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'
import VendorsView from '../views/VendorsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView, meta: { public: true, guestOnly: true } },
    { path: '/register', name: 'register', component: RegisterView, meta: { public: true, guestOnly: true } },
    { path: '/forgot-password', name: 'forgot-password', component: ForgotPasswordView, meta: { public: true } },
    { path: '/reset-password/:uid/:token', name: 'reset-password', component: ResetPasswordView, meta: { public: true } },
    { path: '/no-access', name: 'no-access', component: NoAccessView, meta: { requiresAuth: true } },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'dashboard', component: DashboardView, meta: { blockedRoles: ['vendor'] } },
        { path: 'vendors', name: 'vendors', component: VendorsView, meta: { blockedRoles: ['vendor'] } },
        { path: 'rfqs', name: 'rfqs', component: ComingSoon, meta: { title: "RFQ's" } },
        { path: 'quotations', name: 'quotations', component: ComingSoon, meta: { title: 'Quotations' } },
        { path: 'approvals', name: 'approvals', component: ComingSoon, meta: { title: 'Approvals' } },
        { path: 'purchase-orders', name: 'purchase-orders', component: ComingSoon, meta: { title: 'Purchase orders' } },
        { path: 'invoices', name: 'invoices', component: ComingSoon, meta: { title: 'Invoices' } },
        { path: 'reports', name: 'reports', component: ComingSoon, meta: { title: 'Reports' } },
        { path: 'activity', name: 'activity', component: ComingSoon, meta: { title: 'Activity' } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuth()

  if (to.meta.requiresAuth && !auth.isLoggedIn) return { name: 'login' }
  if (to.meta.guestOnly && auth.isLoggedIn) return { name: 'dashboard' }
  if (to.meta.blockedRoles?.includes(auth.role)) return { name: 'no-access' }
})

export default router
