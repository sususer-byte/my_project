import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSettingsStore = defineStore('settings', () => {
  const provider = ref('OpenAI')

  const characterScale = ref(1)

  const currentTab = ref('AI')

  return {
    provider,
    characterScale,
    currentTab
  }
})
