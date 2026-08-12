/**
 * usePlayerStore — 播放控件状态
 * 管理遥测回放的播放/暂停/倍速/时间轴
 */
import { defineStore } from 'pinia'

export const usePlayerStore = defineStore('player', {
  state() {
    return {
      isPlaying: false,
      currentTime: 0,     // 当前播放时间（秒）
      totalTime: 0,       // 总时长（秒）
      speed: 1,           // 播放倍速 0.5 / 1 / 2 / 4
      speedOptions: [0.5, 1, 2, 4],
      _timer: null,       // 内部定时器
      _lastTick: 0,       // 上次 tick 时间戳
    }
  },

  getters: {
    progress: (state) => {
      if (!state.totalTime) return 0
      return Math.min(100, (state.currentTime / state.totalTime) * 100)
    },
    formattedCurrent: (state) => {
      return formatTime(state.currentTime)
    },
    formattedTotal: (state) => {
      return formatTime(state.totalTime)
    },
  },

  actions: {
    setTotalTime(t) {
      this.totalTime = t
    },

    setCurrentTime(t) {
      this.currentTime = Math.max(0, Math.min(t, this.totalTime))
    },

    play() {
      if (this.isPlaying) return
      if (this.currentTime >= this.totalTime) {
        this.currentTime = 0
      }
      this.isPlaying = true
      this._lastTick = Date.now()
      this._startTimer()
    },

    pause() {
      this.isPlaying = false
      this._stopTimer()
    },

    toggle() {
      if (this.isPlaying) this.pause()
      else this.play()
    },

    reset() {
      this.pause()
      this.currentTime = 0
    },

    setSpeed(s) {
      this.speed = s
    },

    seek(time) {
      this.setCurrentTime(time)
    },

    _startTimer() {
      this._stopTimer()
      this._timer = setInterval(() => {
        const now = Date.now()
        const dt = (now - this._lastTick) / 1000 * this.speed
        this._lastTick = now
        this.currentTime += dt
        if (this.currentTime >= this.totalTime) {
          this.currentTime = this.totalTime
          this.pause()
        }
      }, 50) // 20fps
    },

    _stopTimer() {
      if (this._timer) {
        clearInterval(this._timer)
        this._timer = null
      }
    },
  },
})

function formatTime(seconds) {
  if (!seconds || seconds < 0) return '0:00.0'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 10)
  return `${m}:${String(s).padStart(2, '0')}.${ms}`
}
