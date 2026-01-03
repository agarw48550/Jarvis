import { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage } from 'electron';
import path from 'path';
import { spawn, ChildProcess } from 'child_process';

declare const MAIN_WINDOW_WEBPACK_ENTRY: string;
declare const MAIN_WINDOW_PRELOAD_WEBPACK_ENTRY: string;

let pythonProcess: ChildProcess | null = null;
let tray: Tray | null = null;
let mainWindow: BrowserWindow | null = null;

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (require('electron-squirrel-startup')) {
  app.quit();
}

const startPythonBackend = () => {
  const scriptPath = path.join(__dirname, '../../python/main.py');
  console.log('Starting Python backend from:', scriptPath);

  // Prefer python3.11, fallback to python3
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3.11';

  pythonProcess = spawn(pythonCmd, [scriptPath]);

  pythonProcess.stdout?.on('data', (data) => {
    console.log(`[Python]: ${data} `);
  });

  pythonProcess.stderr?.on('data', (data) => {
    console.error(`[Python API Error]: ${data} `);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code} `);
  });
};

const createTray = () => {
  const iconPath = path.join(__dirname, '../../assets/iconTemplate.png');
  const icon = nativeImage.createFromPath(iconPath).resize({ width: 22, height: 22 });

  tray = new Tray(icon);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show Jarvis',
      click: () => mainWindow?.show()
    },
    {
      label: 'Restart Backend',
      click: () => {
        if (pythonProcess) pythonProcess.kill();
        startPythonBackend();
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => app.quit()
    }
  ]);

  tray.setToolTip('Jarvis AI');
  tray.setContextMenu(contextMenu);

  // Toggle window on click
  tray.on('click', () => {
    if (mainWindow?.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow?.show();
      mainWindow?.focus();
    }
  });
};

const createWindow = () => {
  // Create the browser window.
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    frame: false, // Frameless window
    titleBarStyle: 'hidden',
    titleBarOverlay: {
      color: '#0f172a',
      symbolColor: '#ffffff',
      height: 30
    },
    webPreferences: {
      preload: MAIN_WINDOW_PRELOAD_WEBPACK_ENTRY,
      nodeIntegration: true,
      contextIsolation: false,
      webSecurity: false,
    },
    backgroundColor: '#0f172a',
    show: false, // Don't show immediately
  });

  mainWindow.loadURL(MAIN_WINDOW_WEBPACK_ENTRY);

  // Show when ready to avoid flicker
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  // Prevent closing, just hide (Mac style)
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow?.hide();
    }
    return false;
  });
};

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.on('ready', () => {
  startPythonBackend();
  createWindow();
  createTray();

  // Global shortcut could be added here (e.g. Cmd+Shift+Space)
});

let isQuitting = false;

app.on('before-quit', () => {
  isQuitting = true;
});

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('quit', () => {
  if (pythonProcess) {
    pythonProcess.kill();
  }
});

app.on('activate', () => {
  // On OS X it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and import them here.
import './ipc-handlers';
