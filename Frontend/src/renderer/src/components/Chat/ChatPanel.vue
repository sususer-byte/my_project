<script setup lang="ts">
import { useUIStore } from '../../stores/ui'

const ui = useUIStore()
</script>

<template>
  <div
    class="absolute left-0 top-0 h-full w-96 bg-zinc-900/90 backdrop-blur-md border-r border-zinc-700 transition-transform duration-300"
    :class="ui.chatOpen ? 'translate-x-0' : '-translate-x-full'"
  >
    <!-- Header -->
    <div class="flex items-center justify-between p-5 border-b border-zinc-800">
      <h2 class="text-xl font-bold">Chat</h2>

      <button @click="ui.toggleChat()" class="w-8 h-8 rounded-lg hover:bg-zinc-800 transition">
        ✕
      </button>
    </div>

    <!-- Body -->
    <div class="p-4">Content</div>
  </div>
</template>
