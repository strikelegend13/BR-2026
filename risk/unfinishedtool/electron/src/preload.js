const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  startMonitoring: () => ipcRenderer.invoke('start-monitoring'),
  stopMonitoring: () => ipcRenderer.invoke('stop-monitoring'),
  getMonitoringStatus: () => ipcRenderer.invoke('get-monitoring-status'),
  updateMonitoringSettings: (settings) => ipcRenderer.invoke('update-monitoring-settings', settings),
  getAlerts: () => ipcRenderer.invoke('get-alerts'),
  
  // AI Agent API
  startAI: () => ipcRenderer.invoke('start-ai'),
  stopAI: () => ipcRenderer.invoke('stop-ai'),
  getAIStatus: () => ipcRenderer.invoke('get-ai-status'),
  chatWithAI: (message) => ipcRenderer.invoke('chat-with-ai', message),
}); 
