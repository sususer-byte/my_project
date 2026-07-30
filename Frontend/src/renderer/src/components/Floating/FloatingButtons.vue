<script setup lang="ts">
import { useUIStore } from '../../stores/ui'

const ui = useUIStore()
</script>

<template>
  <div class="absolute right-6 bottom-6 flex flex-col gap-3">
    <button
      @click="ui.toggleSettings()"
      class="w-14 h-14 rounded-full bg-zinc-800 hover:bg-zinc-700 transition"
    >
      ⚙
    </button>

    <button
      @click="ui.toggleChat()"
      class="w-14 h-14 rounded-full bg-blue-600 hover:bg-blue-500 transition"
    >
      💬
    </button>
  </div>
</template>
