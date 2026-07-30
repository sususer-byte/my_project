<script setup lang="ts">
import { useUIStore } from '../../stores/ui'
import { useSettingsStore } from '@renderer/stores/settings'

const ui = useUIStore()
const settings = useSettingsStore()
</script>

<template>
  <div
    class="absolute right-0 top-0 h-full w-96 bg-zinc-900/90 backdrop-blur-xl border-l border-zinc-800 transition-transform duration-300"
    :class="ui.settingsOpen ? 'translate-x-0' : 'translate-x-full'"
  >
    <!--Nút tắt-->
    <div class="flex items-center justify-between p-6 border-b border-zinc-800">
      <h2 class="text-2xl font-bold">Settings</h2>

      <button @click="ui.toggleSettings()" class="w-8 h-8 rounded-lg hover:bg-zinc-800 transition">
        ✕
      </button>
    </div>
    <div class="h-full flex">
      <!-- Sidebar -->
      <div class="w-32 border-r border-zinc-800 p-3">
        <button class="w-full text-left rounded-lg p-2 hover:bg-zinc-800">🤖 Character</button>

        <button class="mt-2 w-full text-left rounded-lg p-2 hover:bg-zinc-800">🧠 AI</button>

        <button class="mt-2 w-full text-left rounded-lg p-2 hover:bg-zinc-800">🎤 Voice</button>

        <button class="mt-2 w-full text-left rounded-lg p-2 hover:bg-zinc-800">⚙ System</button>
      </div>

      <!-- Content -->
      <div class="flex-1 p-6">
        <h2 class="text-2xl font-bold mb-6">AI Settings</h2>

        <div class="mb-5">
          <label class="block mb-2"> LLM Provider </label>

          <select
            v-model="settings.provider"
            class="w-full rounded-lg bg-zinc-800 border border-zinc-700 p-3"
          >
            <option>OpenAI</option>
            <option>Gemini</option>
            <option>OpenRouter</option>
            <option>Ollama</option>
            <option>LM Studio</option>
          </select>
        </div>

        <div>
          <label class="block mb-2"> Character Scale </label>

          <input v-model="settings.characterScale" type="range" min="0.5" max="2" step="0.1" />
          <p class="mt-2 text-zinc-400">
            {{ settings.characterScale }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
