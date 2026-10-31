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
import QuotationCompareView from '../views/QuotationCompareView.vue'
import QuotationFormView from '../views/QuotationFormView.vue'
import QuotationsView from '../views/QuotationsView.vue'
import RfqDetailView from '../views/RfqDetailView.vue'
import RfqFormView from '../views/RfqFormView.vue'
import RfqListView from '../views/RfqListView.vue'
import VendorsView from '../views/VendorsView.vue'

const vendorRoutes = ['vendor']
const editorRoles = ['admin', 'officer']
const comparisonRoles = ['admin', 'officer', 'manager']

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
        { path: 'rfqs', name: 'rfqs', component: RfqListView },
        { path: 'rfqs/new', name: 'rfq-new', component: RfqFormView, meta: { allowedRoles: editorRoles } },
        { path: 'rfqs/:id', name: 'rfq-detail', component: RfqDetailView },
        { path: 'rfqs/:id/edit', name: 'rfq-edit', component: RfqFormView, meta: { allowedRoles: editorRoles } },
        { path: 'rfqs/:id/quote', name: 'rfq-quote', component: QuotationFormView, meta: { allowedRoles: vendorRoutes } },
        { path: 'rfqs/:id/compare', name: 'rfq-compare', component: QuotationCompareView, meta: { allowedRoles: comparisonRoles } },
        { path: 'quotations', name: 'quotations', component: QuotationsView },
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
  const landingPath = auth.role === 'vendor' ? '/rfqs' : '/'

  if (to.meta.requiresAuth && !auth.isLoggedIn) return { name: 'login' }
  if (to.meta.guestOnly && auth.isLoggedIn) return landingPath
  if (to.meta.blockedRoles?.includes(auth.role)) return { name: 'no-access' }
  if (to.meta.allowedRoles && !to.meta.allowedRoles.includes(auth.role)) return { name: 'no-access' }

  if (to.path === '/' && auth.role === 'vendor') return '/rfqs'
})

export default router
