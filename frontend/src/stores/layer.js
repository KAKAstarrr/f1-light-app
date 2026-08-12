/**
 * useLayerStore — 遥测大屏图层开关状态
 * 6 个图层独立控制，全局共享
 */
import { defineStore } from 'pinia'

export const useLayerStore = defineStore('layer', {
  state() {
    return {
      // 6 个图层开关
      trackMap: true,      // 赛道底图
      speed: true,         // 速度曲线
      throttleBrake: true, // 油门/刹车
      lapDistribution: false, // 圈速分布
      sectorFastest: false,   // 分段最快
      delta: false,           // 车手时间差

      // 显示模式：map / chart / split
      viewMode: 'map',

      // 图层数据可用性（由后端返回决定，控制 disabled 状态）
      layerAvailability: {
        trackMap: true,
        speed: true,
        throttleBrake: true,
        lapDistribution: true,
        sectorFastest: true,
        delta: true,
      },
    }
  },

  getters: {
    activeLayers: (state) => {
      const layers = []
      if (state.trackMap) layers.push('trackMap')
      if (state.speed) layers.push('speed')
      if (state.throttleBrake) layers.push('throttleBrake')
      if (state.lapDistribution) layers.push('lapDistribution')
      if (state.sectorFastest) layers.push('sectorFastest')
      if (state.delta) layers.push('delta')
      return layers
    },
  },

  actions: {
    toggle(layer) {
      if (this.layerAvailability[layer] === false) return
      this[layer] = !this[layer]
    },

    setLayer(layer, value) {
      if (this.layerAvailability[layer] === false && value === true) return
      this[layer] = value
    },

    setViewMode(mode) {
      this.viewMode = mode
    },

    setAvailability(availability) {
      this.layerAvailability = { ...this.layerAvailability, ...availability }
    },

    reset() {
      this.trackMap = true
      this.speed = true
      this.throttleBrake = true
      this.lapDistribution = false
      this.sectorFastest = false
      this.delta = false
      this.viewMode = 'map'
    },
  },
})
