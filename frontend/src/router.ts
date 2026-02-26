import { createRouter, createWebHistory } from 'vue-router'
import ContainersView from './views/ContainersView.vue'
import ContainerDetailView from './views/ContainerDetailView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'containers',
      component: ContainersView
    },
    {
      path: '/container/:id',
      name: 'container-detail',
      component: ContainerDetailView
    }
  ]
})

export default router

