/**
 * 小程序入口文件
 * 管理全局数据和生命周期
 */
App({
  /** 小程序启动时执行：获取系统信息并存入全局数据 */
  onLaunch() {
    // 获取设备系统信息（屏幕尺寸、平台等），供各页面使用
    wx.getSystemInfo({
      success: (res) => {
        this.globalData.systemInfo = res
      }
    })
  },
  /** 全局共享数据 */
  globalData: {
    systemInfo: null,              // 设备系统信息
    baseUrl: 'http://localhost:5000', // API 基础地址（备用）
    discoveredHost: null           // 通过并行探测发现的可用后端地址
  }
})
