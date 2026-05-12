import { createRouter, createWebHistory } from 'vue-router'
import ContainersView from './views/ContainersView.vue'
import ContainerDetailView from './views/ContainerDetailView.vue'
import HostsView from './views/HostsView.vue'
import ConfigView from './views/ConfigView.vue'
import GenerateExporterView from './views/GenerateExporterView.vue'
import PrometheusView from './views/PrometheusView.vue'
import GrafanaView from './views/GrafanaView.vue'
import LoginView from './views/LoginView.vue'
import UsersView from './views/UsersView.vue'
import { accessToken, role } from './auth/session'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/users',
      name: 'users',
      component: UsersView
    },
    {
      path: '/',
      redirect: '/containers'
    },
    {
      path: '/hosts',
      name: 'hosts',
      component: HostsView
    },
    {
      path: '/containers',
      name: 'containers',
      component: ContainersView
    },
    {
      path: '/container/:id',
      name: 'container-detail',
      component: ContainerDetailView
    },
    {
      path: '/container/:id/generate-exporter',
      name: 'generate-exporter',
      component: GenerateExporterView
    },
    {
      path: '/config',
      name: 'config',
      component: ConfigView
    },
    {
      path: '/prometheus',
      name: 'prometheus',
      component: PrometheusView
    },
    {
      path: '/grafana',
      name: 'grafana',
      component: GrafanaView
    }
  ]
})

router.beforeEach((to) => {
  if (to.name === 'login') {
    if (accessToken.value) {
      return { path: '/containers' }
    }
    return true
  }
  if (!accessToken.value) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/users' && role.value !== 'maintainer') {
    return { path: '/containers' }
  }
  return true
})

export default router

