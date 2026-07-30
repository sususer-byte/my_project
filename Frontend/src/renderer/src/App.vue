<script setup lang="ts">
import CharacterCanvas from './components/Character/CharacterCanvas.vue'
import FloatingButtons from './components/Floating/FloatingButtons.vue'
import ChatPanel from './components/Chat/ChatPanel.vue'
import SettingsPanel from './components/Settings/SettingsPanel.vue'
</script>

<template>
  <div class="relative w-screen h-screen bg-zinc-950 overflow-hidden">
    <CharacterCanvas />
    <FloatingButtons />
    <ChatPanel />
    <SettingsPanel />
  </div>
</template>
