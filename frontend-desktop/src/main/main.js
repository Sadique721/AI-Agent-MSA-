const { app, BrowserWindow, globalShortcut, clipboard, Tray, Menu, ipcMain, protocol, net } = require('electron');
const path = require('path');
const { pathToFileURL } = require('url');

protocol.registerSchemesAsPrivileged([
  { scheme: 'media', privileges: { secure: true, supportFetchAPI: true, bypassCSP: true, stream: true } }
]);
const { spawn } = require('child_process');

let mainWindow;
let tray = null;
let isQuitting = false;
let pyProcess = null;
const fs = require('fs');

function logToFile(msg) {
  try {
    const logDir = app.getPath('userData');
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }
    const logPath = path.join(logDir, 'msa-desktop.log');
    fs.appendFileSync(logPath, `[${new Date().toISOString()}] ${msg}\n`);
  } catch (e) {
    console.error(e);
  }
}

function startBackend() {
  try {
    const pyPath = 'd:\\My Self Details\\Programs\\AI\\msa_agent\\.venv\\Scripts\\python.exe';
    const pyWorkingDir = 'd:\\My Self Details\\Programs\\AI\\msa_agent';
    const scriptPath = 'main.py';

    logToFile(`Starting Python backend server: ${pyPath} ${scriptPath} in ${pyWorkingDir}`);
    
    pyProcess = spawn(pyPath, [scriptPath], {
      cwd: pyWorkingDir,
      env: { ...process.env, MSA_AUTO_APPROVE: 'true' }
    });

    pyProcess.stdout.on('data', (data) => {
      logToFile(`Backend stdout: ${data.toString().trim()}`);
    });

    pyProcess.stderr.on('data', (data) => {
      logToFile(`Backend stderr: ${data.toString().trim()}`);
    });

    pyProcess.on('close', (code) => {
      logToFile(`Backend process exited with code ${code}`);
    });

    pyProcess.on('error', (err) => {
      logToFile(`Backend process error: ${err.message}`);
    });
  } catch (err) {
    logToFile(`startBackend exception: ${err.message}`);
  }
}

function killBackend() {
  if (pyProcess) {
    logToFile('Stopping Python backend server...');
    pyProcess.kill('SIGINT');
    pyProcess = null;
  }
}

function startOllama() {
  const ollamaPath = 'C:\\Users\\MD SADIQUE AMIN\\AppData\\Local\\Programs\\Ollama\\ollama.exe';
  logToFile('Checking if Ollama is running...');
  
  const http = require('http');
  const req = http.get('http://127.0.0.1:11434/api/tags', (res) => {
    logToFile('Ollama is already running.');
  });

  req.on('error', (err) => {
    logToFile('Ollama is not running. Starting Ollama daemon...');
    try {
      const fs = require('fs');
      if (fs.existsSync(ollamaPath)) {
        const ollamaProcess = spawn(ollamaPath, [], {
          detached: true,
          stdio: 'ignore'
        });
        ollamaProcess.unref();
        logToFile('Ollama daemon started.');
      } else {
        logToFile(`Ollama executable not found at: ${ollamaPath}`);
      }
    } catch (e) {
      logToFile(`Failed to start Ollama: ${e.message}`);
    }
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    transparent: false,
    frame: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    logToFile(`[Console] ${message} (from ${sourceId}:${line})`);
  });

  // Load local build file or fallback dev server
  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
  if (isDev) {
    mainWindow.loadURL('http://localhost:3000'); // Vite port is 3000
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', '..', 'dist', 'index.html'));
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
  // Load icon from the same folder as the executable (outside ASAR)
  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
  const iconPath = isDev 
    ? path.join(__dirname, '..', '..', 'assets', 'icon.ico')
    : path.join(path.dirname(app.getPath('exe')), 'icon.ico');
  
  logToFile(`Loading Tray icon from: ${iconPath}`);
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
  protocol.handle('media', (request) => {
    const filePath = decodeURIComponent(request.url.replace('media://', ''));
    return net.fetch(pathToFileURL(filePath).toString());
  });

  startOllama();
  startBackend();
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
  killBackend();
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

// IPC handlers for V5 OS Desktop context API integration
ipcMain.handle('read-clipboard', () => {
  return clipboard.readText();
});

ipcMain.handle('write-clipboard', (event, text) => {
  clipboard.writeText(text);
  return true;
});
