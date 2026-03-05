<template>
  <div id="app">
    <header class="header">
      <div class="container">
        <div class="header-content">
          <h1 class="logo">Auto Observability</h1>
          <nav class="nav-tabs">
            <router-link to="/hosts" class="nav-link">Hosts</router-link>
            <router-link to="/containers" class="nav-link">Containers</router-link>
            <router-link to="/prometheus" class="nav-link">Prometheus</router-link>
            <router-link to="/config" class="nav-link">Configuration</router-link>
          </nav>
        </div>
      </div>
    </header>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.header {
  background-color: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  padding: 8px 0;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-tabs {
  display: flex;
  gap: 8px;
}

.logo {
  font-size: 18px;
  font-weight: 600;
  color: var(--accent);
}

.nav-link {
  color: var(--text-primary);
  text-decoration: none;
  padding: 6px 12px;
  border-radius: 6px;
  transition: background-color 0.2s;
  font-size: 14px;
}

.nav-link:hover {
  background-color: var(--bg-primary);
}

.nav-link.router-link-active {
  color: var(--accent);
  background-color: var(--bg-primary);
}

.main {
  min-height: calc(100vh - 60px);
}
</style>

