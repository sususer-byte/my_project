import { defineStore } from 'pinia'

export const useUIStore = defineStore('ui', {
  state: () => ({
    chatOpen: false,
    settingsOpen: false,
    characterScale: 1
  }),

  actions: {
    toggleChat() {
      this.chatOpen = !this.chatOpen
    },

    toggleSettings() {
      this.settingsOpen = !this.settingsOpen
    },

    setCharacterScale(scale: number) {
      this.characterScale = scale
    }
  }
})
