<template>
  <div class="container">
    <ContainerDetails 
      :container-id="containerId"
      @back="goBack"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ContainerDetails from '../components/ContainerDetails.vue'

const router = useRouter()
const route = useRoute()

const containerId = computed(() => route.params.id as string)

const goBack = () => {
  router.push('/')
}
</script>

