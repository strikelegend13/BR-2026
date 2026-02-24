const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fetch = require('node-fetch');

let mainWindow;
const PYTHON_API_URL = 'http://127.0.0.1:5001';

//push

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'assets', 'icon.png'),
    titleBarStyle: 'default',
    show: false
  });

  // Load the app - always use Vite dev server in development
  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
  
  if (isDev) {
    console.log('Loading React app from Vite dev server...');
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
    
    // Add debugging for page load events
    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
      console.error('Failed to load React app:', errorCode, errorDescription);
    });
    
    mainWindow.webContents.on('did-finish-load', () => {
      console.log('React app loaded successfully');
    });
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Helper function to make API calls
async function makeApiCall(endpoint, options = {}) {
  try {
    const response = await fetch(`${PYTHON_API_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });
    
    if (!response.ok) {
      throw new Error(`API call failed: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`API call error: ${error.message}`);
    throw error;
  }
}

// IPC handlers for monitoring
ipcMain.handle('start-monitoring', async () => {
  try {
    const result = await makeApiCall('/monitor/start', {
      method: 'POST'
    });
    console.log('Monitoring started:', result);
    return result;
  } catch (error) {
    console.error('Failed to start monitoring:', error);
    return { success: false, message: error.message };
  }
});

ipcMain.handle('stop-monitoring', async () => {
  try {
    const result = await makeApiCall('/monitor/stop', {
      method: 'POST'
    });
    console.log('Monitoring stopped:', result);
    return result;
  } catch (error) {
    console.error('Failed to stop monitoring:', error);
    return { success: false, message: error.message };
  }
});

ipcMain.handle('get-monitoring-status', async () => {
  try {
    const status = await makeApiCall('/monitor/status');
    console.log('Monitoring status:', status);
    return status;
  } catch (error) {
    console.error('Failed to get monitoring status:', error);
    return { 
      isRunning: false, 
      lastActivity: null, 
      alerts: [],
      error: error.message 
    };
  }
});

ipcMain.handle('update-monitoring-settings', async (event, settings) => {
  try {
    const result = await makeApiCall('/monitor/settings', {
      method: 'PUT',
      body: JSON.stringify(settings)
    });
    console.log('Settings updated:', result);
    return result;
  } catch (error) {
    console.error('Failed to update settings:', error);
    return { success: false, message: error.message };
  }
});

ipcMain.handle('get-alerts', async () => {
  try {
    const result = await makeApiCall('/monitor/alerts');
    return result;
  } catch (error) {
    console.error('Failed to get alerts:', error);
    return { alerts: [] };
  }
});

// AI Agent IPC handlers
ipcMain.handle('start-ai', async () => {
  try {
    const result = await makeApiCall('/ai/start', {
      method: 'POST'
    });
    console.log('AI Agent started:', result);
    return result;
  } catch (error) {
    console.error('Failed to start AI agent:', error);
    return { success: false, message: error.message };
  }
});

ipcMain.handle('stop-ai', async () => {
  try {
    const result = await makeApiCall('/ai/stop', {
      method: 'POST'
    });
    console.log('AI Agent stopped:', result);
    return result;
  } catch (error) {
    console.error('Failed to stop AI agent:', error);
    return { success: false, message: error.message };
  }
});

ipcMain.handle('get-ai-status', async () => {
  try {
    const status = await makeApiCall('/ai/status');
    console.log('AI Agent status:', status);
    return status;
  } catch (error) {
    console.error('Failed to get AI status:', error);
    return { 
      isActive: false, 
      contextMemorySize: 0, 
      conversationHistorySize: 0,
      error: error.message 
    };
  }
});

ipcMain.handle('chat-with-ai', async (event, message) => {
  try {
    const result = await makeApiCall('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message })
    });
    console.log('AI Chat response:', result);
    return result;
  } catch (error) {
    console.error('Failed to chat with AI:', error);
    return { success: false, message: error.message };
  }
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
