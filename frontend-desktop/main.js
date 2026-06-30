const { app, BrowserWindow, globalShortcut, clipboard, Tray, Menu } = require('electron');
const path = require('path');

let mainWindow;
let tray = null;
let isQuitting = false;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    transparent: true,
    frame: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  // Load local build file or fallback dev server
  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  // Intercept window close event to hide instead of quit
  mainWindow.on('close', function (event) {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
    return false;
  });

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

function createTray() {
  // Use a default icon or a fallback dot
  const iconPath = path.join(__dirname, 'icon.png');
  tray = new Tray(iconPath);
  
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Show MSA Agent', click: () => mainWindow.show() },
    { label: 'Hide MSA Agent', click: () => mainWindow.hide() },
    { type: 'separator' },
    { label: 'Exit Application', click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);
  
  tray.setToolTip('MSA AI Agent OS Client');
  tray.setContextMenu(contextMenu);
  
  tray.on('click', () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

app.on('ready', () => {
  createWindow();
  try {
    createTray();
  } catch (e) {
    console.log("Tray icon failed to load, continuing without tray.");
  }

  // Register Cmd+K / Ctrl+K global hotkey to toggle window visibility
  globalShortcut.register('CommandOrControl+K', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
        mainWindow.webContents.send('global-hotkey', 'trigger');
      }
    }
  });
});

app.on('before-quit', () => {
  isQuitting = true;
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', function () {
  if (mainWindow === null) {
    createWindow();
  }
});
