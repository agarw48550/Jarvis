/**
 * File Actions - Read, Write, List files
 */

import fs from 'fs/promises';
import path from 'path';
import { ActionResult } from './index';

export async function handleReadFile(params: {
    path: string;
}): Promise<ActionResult> {
    try {
        // Expand home directory
        const filePath = params.path.replace(/^~/, process.env.HOME || '');

        const content = await fs.readFile(filePath, 'utf-8');

        // Truncate if too long for voice
        const truncated = content.length > 500
            ? content.substring(0, 500) + '... (content truncated)'
            : content;

        return {
            success: true,
            message: `The file contains:  ${truncated}`,
            data: { content, path: filePath },
        };
    } catch (error: any) {
        if (error.code === 'ENOENT') {
            return { success: false, message: `File not found: ${params.path}` };
        }
        return { success: false, message: `Couldn't read file: ${error.message}` };
    }
}

export async function handleWriteFile(params: {
    path: string;
    content: string;
}): Promise<ActionResult> {
    try {
        const filePath = params.path.replace(/^~/, process.env.HOME || '');

        // Ensure directory exists
        await fs.mkdir(path.dirname(filePath), { recursive: true });

        await fs.writeFile(filePath, params.content, 'utf-8');

        return {
            success: true,
            message: `File saved to ${params.path}. `,
            data: { path: filePath },
        };
    } catch (error: any) {
        return { success: false, message: `Couldn't write file: ${error.message}` };
    }
}

export async function handleListFiles(params: {
    path: string;
}): Promise<ActionResult> {
    try {
        const dirPath = params.path.replace(/^~/, process.env.HOME || '');

        const entries = await fs.readdir(dirPath, { withFileTypes: true });

        const files = entries.map(e => ({
            name: e.name,
            type: e.isDirectory() ? 'folder' : 'file',
        }));

        const summary = files.slice(0, 10).map(f =>
            `${f.type === 'folder' ? '📁' : '📄'} ${f.name}`
        ).join(', ');

        return {
            success: true,
            message: `Found ${files.length} items:  ${summary}${files.length > 10 ? '.. .' : ''}`,
            data: { files },
        };
    } catch (error: any) {
        return { success: false, message: `Couldn't list files:  ${error.message}` };
    }
}
