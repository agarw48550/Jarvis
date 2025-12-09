/**
 * System Actions - Open apps, control volume, etc.
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import { ActionResult } from './index';

const execAsync = promisify(exec);

export async function handleOpenApp(params: {
    app_name: string;
}): Promise<ActionResult> {
    const appName = params.app_name;

    try {
        const platform = process.platform;

        if (platform === 'darwin') {
            // macOS
            await execAsync(`open -a "${appName}"`);
        } else if (platform === 'win32') {
            // Windows
            await execAsync(`start "" "${appName}"`);
        } else {
            // Linux
            await execAsync(`xdg-open "${appName}" || ${appName.toLowerCase()}`);
        }

        return {
            success: true,
            message: `Opened ${appName}. `,
        };
    } catch (error) {
        return {
            success: false,
            message: `Couldn't open ${appName}. Make sure the app is installed.`,
        };
    }
}

export async function handleControlVolume(params: {
    level?: number;
    action?: 'up' | 'down' | 'mute' | 'unmute';
}): Promise<ActionResult> {
    try {
        const platform = process.platform;

        if (platform === 'darwin') {
            if (params.level !== undefined) {
                await execAsync(`osascript -e "set volume output volume ${params.level}"`);
                return { success: true, message: `Volume set to ${params.level}%.` };
            }

            if (params.action === 'mute') {
                await execAsync('osascript -e "set volume output muted true"');
                return { success: true, message: 'Muted.' };
            }

            if (params.action === 'unmute') {
                await execAsync('osascript -e "set volume output muted false"');
                return { success: true, message: 'Unmuted.' };
            }
        }

        return { success: false, message: 'Volume control not supported on this platform yet.' };
    } catch (error) {
        return { success: false, message: `Volume control failed: ${error}` };
    }
}

export async function handleTakeScreenshot(params: {}): Promise<ActionResult> {
    try {
        const platform = process.platform;
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `jarvis-screenshot-${timestamp}.png`;

        let savePath: string;

        if (platform === 'darwin') {
            savePath = `~/Desktop/${filename}`;
            await execAsync(`screencapture -x ${savePath}`);
        } else if (platform === 'win32') {
            // Windows - use PowerShell
            savePath = `$env:USERPROFILE\\Desktop\\${filename}`;
            await execAsync(`powershell -c "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen | ForEach-Object { $bitmap = New-Object System.Drawing.Bitmap($_.Bounds.Width, $_.Bounds.Height); $graphics = [System.Drawing.Graphics]::FromImage($bitmap); $graphics.CopyFromScreen($_.Bounds.Location, [System.Drawing.Point]::Empty, $_.Bounds.Size); $bitmap.Save('${savePath}') }"`);
        } else {
            return { success: false, message: 'Screenshot not supported on this platform yet.' };
        }

        return {
            success: true,
            message: `Screenshot saved to Desktop. `,
            data: { path: savePath },
        };
    } catch (error) {
        return { success: false, message: `Screenshot failed: ${error}` };
    }
}
