<template>
  <div class="hierarchy-node" :style="{ '--depth': depth }">
    <div class="node-header">
      <span v-if="hasChildren" class="toggle-indicator" :class="{ expanded: isExpanded }" @click="toggleExpanded"></span>
      <span v-else class="toggle-spacer"></span>
      <a :href="wikibaseUrl(node.id)" target="_blank" rel="noopener" class="node-link" @click.stop>
        <span class="node-label" :class="'depth-' + Math.min(depth, 2)">{{ titleCase(node.label) }}</span>
      </a>
      <span class="node-id">{{ node.id }}</span>
    </div>

    <div v-show="isExpanded" class="node-body">
      <div class="node-detail">
        <img
          v-if="node.thumbnail && node.thumbnail.length"
          class="node-thumbnail"
          :src="transparentUrl(node.thumbnail[0])"
          :alt="node.label"
          loading="lazy"
        />
        <div class="node-info">
          <p v-if="node.description" class="node-description">{{ node.description }}</p>

          <div v-if="hasMetadata" class="node-meta">
            <div v-if="node.used_in && node.used_in.length" class="meta-row">
              <span class="meta-label">Used in</span>
              <span class="meta-values">
                <span v-for="(item, i) in node.used_in" :key="item.id" class="used-in-tag">
                  <a :href="wikibaseUrl(item.id)" target="_blank" rel="noopener" class="wiki-link">{{ item.label }}</a><span v-if="i < node.used_in.length - 1" class="meta-sep">&middot;</span>
                </span>
              </span>
            </div>

            <div v-if="node.ieee_term && node.ieee_term.length" class="meta-row">
              <span class="meta-label">IEEE Term</span>
              <span class="meta-values">{{ node.ieee_term.join(', ') }}</span>
            </div>

            <div v-if="node.exact_match && node.exact_match.length" class="meta-row">
              <span class="meta-label">Exact Match</span>
              <span class="meta-values">
                <a
                  v-for="uri in node.exact_match"
                  :key="uri"
                  :href="uri"
                  target="_blank"
                  rel="noopener"
                  class="match-link"
                >{{ shortenUri(uri) }}</a>
              </span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="hasChildren" class="node-children">
        <HierarchyNode
          v-for="(child, index) in children"
          :key="child.id + '-' + index"
          :node="child"
          :search-query="searchQuery"
          :depth="depth + 1"
        />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'HierarchyNode',
  props: {
    node: { type: Object, required: true },
    searchQuery: { type: String, default: '' },
    depth: { type: Number, default: 0 }
  },
  data() {
    return {
      expanded: true
    }
  },
  computed: {
    children() {
      return [...(this.node.subclasses || []), ...(this.node.instances || [])]
    },
    hasChildren() {
      return this.children.length > 0
    },
    isExpanded() {
      if (this.searchQuery) return true
      return this.expanded
    },
    hasMetadata() {
      const n = this.node
      return (n.used_in && n.used_in.length) ||
             (n.ieee_term && n.ieee_term.length) ||
             (n.exact_match && n.exact_match.length)
    }
  },
  methods: {
    titleCase(str) {
      return str.replace(/\b\w/g, c => c.toUpperCase())
    },
    wikibaseUrl(qid) {
      return 'https://base.semlab.io/wiki/Item:' + qid
    },
    transparentUrl(url) {
      return url.replace(/([^/]+)\.jpg$/, (_, name) => name + '_transparent.png')
    },
    toggleExpanded() {
      if (!this.searchQuery) {
        this.expanded = !this.expanded
      }
    },
    shortenUri(uri) {
      try {
        const u = new URL(uri)
        return u.hostname + u.pathname
      } catch {
        return uri
      }
    }
  },
  watch: {
    'node.id'() {
      this.expanded = true
    }
  }
}
</script>

<style scoped>
.hierarchy-node {
  margin-left: calc(var(--depth, 0) * 2rem);
  border-left: 1px solid var(--color-rule-light, #c4bba8);
  padding-left: 1rem;
  margin-bottom: 0.5rem;
}

.hierarchy-node:last-child {
  margin-bottom: 0;
}

.node-header {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  padding: 0.35rem 0;
  user-select: none;
}

.node-link {
  text-decoration: none;
  color: inherit;
}

.node-link:hover .node-label {
  color: var(--color-accent, #c43e1c);
}

.toggle-indicator {
  display: inline-block;
  width: 0;
  height: 0;
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  border-left: 7px solid var(--color-ink, #1a1a17);
  flex-shrink: 0;
  transition: transform 0.15s;
  margin-top: 2px;
  cursor: pointer;
}

.toggle-indicator.expanded {
  transform: rotate(90deg);
}

.toggle-spacer {
  display: inline-block;
  width: 7px;
  flex-shrink: 0;
}

.node-label {
  font-family: 'Playfair Display', Georgia, serif;
  font-weight: 700;
  transition: color 0.1s;
}

.node-label.depth-0 {
  font-size: 1.7rem;
}

.node-label.depth-1 {
  font-size: 1.4rem;
}

.node-label.depth-2 {
  font-size: 1.2rem;
}

.node-id {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.75rem;
  color: var(--color-rule, #8b8578);
  flex-shrink: 0;
}

.node-body {
  padding-bottom: 0.25rem;
}

.node-detail {
  display: flex;
  gap: 1rem;
  padding: 0.25rem 0 0.5rem;
}

.node-thumbnail {
  width: 100px;
  height: 75px;
  object-fit: contain;
  flex-shrink: 0;
}

.node-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.node-description {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.9rem;
  line-height: 1.55;
  color: var(--color-ink-light, #4a4a42);
  margin: 0 0 0.4rem;
}

.node-meta {
  border-top: 1px dashed var(--color-rule, #8b8578);
  padding-top: 0.35rem;
}

.meta-row {
  margin-bottom: 0.2rem;
}

.meta-label {
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-ink-light, #4a4a42);
  white-space: nowrap;
  margin-right: 0.4rem;
}

.meta-values {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.85rem;
  color: var(--color-ink, #1a1a17);
  line-height: 1.7;
  display: inline;
}

.meta-sep {
  margin: 0 0.35rem;
  color: var(--color-rule, #8b8578);
}

.wiki-link {
  text-decoration: none;
  color: inherit;
}

.wiki-link:hover {
  color: var(--color-accent, #c43e1c);
}

.match-link {
  display: inline-block;
  color: var(--color-accent, #c43e1c);
  text-decoration: none;
  margin-right: 0.75rem;
  word-break: break-all;
}

.match-link:hover {
  text-decoration: underline;
}

.node-children {
  margin-top: 0.25rem;
}
</style>
