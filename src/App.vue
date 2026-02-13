<template>
  <div class="app">
    <header class="masthead">
      <div class="masthead-rule"></div>
      <h1>E.A.T.</h1>
      <p class="subtitle">Experiments in Art and Technology — Hierarchy Browser</p>
      <div class="masthead-rule"></div>
    </header>

    <nav v-if="hierarchy.length" class="category-tabs">
      <button
        v-for="root in hierarchy"
        :key="root.id"
        :class="{ active: activeCategory === root.id }"
        @click="selectCategory(root.id)"
      >{{ root.label }}</button>
    </nav>

    <div class="search-bar">
      <input
        type="text"
        v-model="searchQuery"
        :placeholder="searchPlaceholder"
      />
      <span v-if="searchQuery && activeRoot" class="search-count">
        {{ resultCount }} item{{ resultCount !== 1 ? 's' : '' }} found
      </span>
    </div>

    <main class="content">
      <div v-if="loading" class="status-message">Loading hierarchy data...</div>
      <div v-else-if="error" class="status-message error">{{ error }}</div>

      <template v-else-if="activeRoot">
        <div v-if="activeRoot.description" class="category-header">
          <p class="category-description">{{ activeRoot.description }}</p>
        </div>

        <div v-if="displayedNodes.length === 0 && searchQuery" class="status-message">
          No items matching "{{ searchQuery }}"
        </div>

        <div class="hierarchy-tree">
          <HierarchyNode
            v-for="(node, index) in displayedNodes"
            :key="node.id + '-' + index"
            :node="node"
            :search-query="searchQuery"
            :depth="0"
          />
        </div>
      </template>

      <div v-else class="status-message">Select a category above to browse.</div>
    </main>

    <footer class="footer">
      <div class="footer-rule"></div>
      <p>Semantic Lab at Pratt Institute &middot; Data from Wikibase</p>
    </footer>
  </div>
</template>

<script>
import HierarchyNode from './components/HierarchyNode.vue'

export default {
  name: 'App',
  components: { HierarchyNode },
  data() {
    return {
      hierarchy: [],
      activeCategory: null,
      searchQuery: '',
      loading: true,
      error: null
    }
  },
  computed: {
    activeRoot() {
      return this.hierarchy.find(r => r.id === this.activeCategory) || null
    },
    displayedNodes() {
      if (!this.activeRoot) return []
      const children = [
        ...(this.activeRoot.subclasses || []),
        ...(this.activeRoot.instances || [])
      ]
      if (!this.searchQuery.trim()) return children
      return this.filterTree(children, this.searchQuery.toLowerCase().trim())
    },
    resultCount() {
      if (!this.searchQuery.trim()) return 0
      return this.countNodes(this.displayedNodes)
    },
    searchPlaceholder() {
      if (this.activeRoot) {
        return 'Search within ' + this.activeRoot.label + '...'
      }
      return 'Search...'
    }
  },
  methods: {
    selectCategory(id) {
      this.activeCategory = id
    },
    filterTree(nodes, query) {
      return nodes.reduce((acc, node) => {
        const labelMatch = (node.label || '').toLowerCase().includes(query)
        const descMatch = (node.description || '').toLowerCase().includes(query)
        const selfMatch = labelMatch || descMatch
        const filteredSubclasses = this.filterTree(node.subclasses || [], query)
        const filteredInstances = this.filterTree(node.instances || [], query)
        const hasMatchingChildren = filteredSubclasses.length > 0 || filteredInstances.length > 0
        if (selfMatch || hasMatchingChildren) {
          const filtered = { ...node }
          if (filteredSubclasses.length) {
            filtered.subclasses = filteredSubclasses
          } else {
            delete filtered.subclasses
          }
          if (filteredInstances.length) {
            filtered.instances = filteredInstances
          } else {
            delete filtered.instances
          }
          acc.push(filtered)
        }
        return acc
      }, [])
    },
    countNodes(nodes) {
      return nodes.reduce((sum, n) => {
        return sum + 1 +
          this.countNodes(n.subclasses || []) +
          this.countNodes(n.instances || [])
      }, 0)
    }
  },
  async created() {
    try {
      const base = import.meta.env.BASE_URL
      const res = await fetch(base + 'data/enriched_hierarchy.json')
      const data = await res.json()
      this.hierarchy = data.hierarchy
      if (this.hierarchy.length > 0) {
        this.activeCategory = this.hierarchy[0].id
      }
    } catch (e) {
      this.error = 'Failed to load hierarchy data.'
      console.error(e)
    } finally {
      this.loading = false
    }
  }
}
</script>

<style>
:root {
  --color-parchment: #f4edd8;
  --color-parchment-dark: #e8dfc6;
  --color-ink: #1a1a17;
  --color-ink-light: #4a4a42;
  --color-accent: #c43e1c;
  --color-rule: #8b8578;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background: linear-gradient(170deg, #f5eedd 0%, #ede4cc 40%, #e3d8be 100%);
  min-height: 100vh;
  color: var(--color-ink);
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
}
</style>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ── Masthead ── */

.masthead {
  text-align: center;
  padding: 2rem 1rem 1.2rem;
}

.masthead-rule {
  height: 3px;
  background: var(--color-ink);
  max-width: 700px;
  margin: 0 auto;
}

.masthead h1 {
  font-family: 'Playfair Display', Georgia, serif;
  font-weight: 900;
  font-size: 3.5rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  margin: 0.6rem 0 0.3rem;
  line-height: 1;
}

.subtitle {
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 400;
  font-size: 0.88rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-ink-light);
  margin-bottom: 0.6rem;
}

/* ── Category Tabs ── */

.category-tabs {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0;
  border-bottom: 2px solid var(--color-ink);
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
  padding: 0 1rem;
}

.category-tabs button {
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 600;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.65rem 1.2rem;
  border: none;
  background: transparent;
  color: var(--color-ink-light);
  cursor: pointer;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}

.category-tabs button.active {
  color: var(--color-ink);
  border-bottom-color: var(--color-accent);
  background: rgba(0, 0, 0, 0.04);
}

.category-tabs button:hover:not(.active) {
  color: var(--color-ink);
  background: rgba(0, 0, 0, 0.02);
}

/* ── Search ── */

.search-bar {
  max-width: 700px;
  margin: 1.2rem auto 0;
  padding: 0 1rem;
  position: relative;
}

.search-bar input {
  width: 100%;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.95rem;
  padding: 0.55rem 0.8rem;
  border: 2px solid var(--color-rule);
  background: rgba(255, 255, 255, 0.45);
  color: var(--color-ink);
  outline: none;
  transition: border-color 0.15s;
}

.search-bar input::placeholder {
  color: var(--color-rule);
}

.search-bar input:focus {
  border-color: var(--color-ink);
}

.search-count {
  display: block;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.8rem;
  color: var(--color-ink-light);
  margin-top: 0.3rem;
  letter-spacing: 0.03em;
}

/* ── Content ── */

.content {
  max-width: 900px;
  margin: 0 auto;
  padding: 1rem 1.5rem 3rem;
  width: 100%;
  flex: 1;
}

.category-header {
  border-bottom: 1px dashed var(--color-rule);
  padding-bottom: 0.8rem;
  margin-bottom: 1rem;
}

.category-description {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--color-ink-light);
}

.status-message {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.95rem;
  color: var(--color-ink-light);
  text-align: center;
  padding: 3rem 1rem;
}

.status-message.error {
  color: var(--color-accent);
}

.hierarchy-tree {
  margin-top: 0.5rem;
}

/* ── Footer ── */

.footer {
  text-align: center;
  padding: 1rem;
  margin-top: auto;
}

.footer-rule {
  height: 2px;
  background: var(--color-ink);
  max-width: 700px;
  margin: 0 auto 0.8rem;
}

.footer p {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.8rem;
  color: var(--color-rule);
  letter-spacing: 0.05em;
}
</style>
