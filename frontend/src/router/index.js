import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../stores/auth'
import AppLayout from '../components/AppLayout.vue'
import ApprovalDetailView from '../views/ApprovalDetailView.vue'
import ApprovalListView from '../views/ApprovalListView.vue'
import DashboardView from '../views/DashboardView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import LoginView from '../views/LoginView.vue'
import NoAccessView from '../views/NoAccessView.vue'
import NotFoundView from '../views/NotFoundView.vue'
import ActivityView from '../views/ActivityView.vue'
import NotificationsView from '../views/NotificationsView.vue'
import ReportsView from '../views/ReportsView.vue'
import InvoiceDetailView from '../views/InvoiceDetailView.vue'
import InvoiceListView from '../views/InvoiceListView.vue'
import PurchaseOrderDetailView from '../views/PurchaseOrderDetailView.vue'
import PurchaseOrderListView from '../views/PurchaseOrderListView.vue'
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
const approvalRoles = ['admin', 'officer', 'manager']
const reportRoles = ['admin', 'officer', 'manager']
const purchaseOrderRoles = ['admin', 'officer', 'manager', 'vendor']

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView, meta: { public: true, guestOnly: true, title: 'Login' } },
    { path: '/register', name: 'register', component: RegisterView, meta: { public: true, guestOnly: true, title: 'Register' } },
    { path: '/forgot-password', name: 'forgot-password', component: ForgotPasswordView, meta: { public: true, title: 'Forgot password' } },
    { path: '/reset-password/:uid/:token', name: 'reset-password', component: ResetPasswordView, meta: { public: true, title: 'Reset password' } },
    { path: '/no-access', name: 'no-access', component: NoAccessView, meta: { requiresAuth: true, title: 'No access' } },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'dashboard', component: DashboardView, meta: { blockedRoles: ['vendor'], title: 'Dashboard' } },
        { path: 'vendors', name: 'vendors', component: VendorsView, meta: { blockedRoles: ['vendor'], title: 'Vendors' } },
        { path: 'rfqs', name: 'rfqs', component: RfqListView, meta: { title: 'RFQs' } },
        { path: 'rfqs/new', name: 'rfq-new', component: RfqFormView, meta: { allowedRoles: editorRoles, title: 'New RFQ' } },
        { path: 'rfqs/:id', name: 'rfq-detail', component: RfqDetailView, meta: { title: 'RFQ' } },
        { path: 'rfqs/:id/edit', name: 'rfq-edit', component: RfqFormView, meta: { allowedRoles: editorRoles, title: 'Edit RFQ' } },
        { path: 'rfqs/:id/quote', name: 'rfq-quote', component: QuotationFormView, meta: { allowedRoles: vendorRoutes, title: 'Submit quotation' } },
        { path: 'rfqs/:id/compare', name: 'rfq-compare', component: QuotationCompareView, meta: { allowedRoles: comparisonRoles, title: 'Compare quotations' } },
        { path: 'quotations', name: 'quotations', component: QuotationsView, meta: { title: 'Quotations' } },
        { path: 'approvals', name: 'approvals', component: ApprovalListView, meta: { allowedRoles: approvalRoles, title: 'Approvals' } },
        { path: 'approvals/:id', name: 'approval-detail', component: ApprovalDetailView, meta: { allowedRoles: approvalRoles, title: 'Approval' } },
        { path: 'purchase-orders', name: 'purchase-orders', component: PurchaseOrderListView, meta: { allowedRoles: purchaseOrderRoles, title: 'Purchase orders' } },
        { path: 'purchase-orders/:id', name: 'purchase-order-detail', component: PurchaseOrderDetailView, meta: { allowedRoles: purchaseOrderRoles, title: 'Purchase order' } },
        { path: 'invoices', name: 'invoices', component: InvoiceListView, meta: { allowedRoles: purchaseOrderRoles, title: 'Invoices' } },
        { path: 'invoices/:id', name: 'invoice-detail', component: InvoiceDetailView, meta: { allowedRoles: purchaseOrderRoles, title: 'Invoice' } },
        { path: 'notifications', name: 'notifications', component: NotificationsView, meta: { title: 'Notifications' } },
        { path: 'reports', name: 'reports', component: ReportsView, meta: { allowedRoles: reportRoles, title: 'Reports & analytics' } },
        { path: 'activity', name: 'activity', component: ActivityView, meta: { allowedRoles: reportRoles, title: 'Activity & Logs' } },
        { path: ':pathMatch(.*)*', name: 'not-found', component: NotFoundView, meta: { title: 'Page not found' } },
      ],
    },
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

  document.title = `${to.meta.title || 'VendorBridge'} - VendorBridge`
})

export default router
