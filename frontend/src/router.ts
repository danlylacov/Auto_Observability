import { createRouter, createWebHistory } from 'vue-router'
import ContainersView from './views/ContainersView.vue'
import ContainerDetailView from './views/ContainerDetailView.vue'
import HostsView from './views/HostsView.vue'
import ConfigView from './views/ConfigView.vue'
import GenerateExporterView from './views/GenerateExporterView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
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
    }
  ]
})

export default router

