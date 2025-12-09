import { ipcMain } from 'electron';
import { net } from 'electron';

// Placeholder for IPC handlers
// We will implement actual handlers when we set up the Python backend

ipcMain.on('message-from-renderer', (event, arg) => {
    console.log(arg); // Print to console
    event.reply('message-to-renderer', 'pong');
});
