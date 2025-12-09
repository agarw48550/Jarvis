/**
 * Bridge to communicate with Python backend
 */

const PYTHON_API = 'http://localhost:5000';

interface HealthResponse {
    status: string;
    listening: boolean;
    services: Record<string, string>;
}

interface TranscribeResponse {
    text: string;
    success: boolean;
    error?: string;
}

interface TTSResponse {
    audio_path: string;
    success: boolean;
    error?: string;
}

interface RecordResponse {
    audio_path: string;
    audio_base64: string;
    success: boolean;
    error?: string;
}

class PythonBridge {
    private baseUrl: string;

    constructor(baseUrl: string = PYTHON_API) {
        this.baseUrl = baseUrl;
    }

    async checkHealth(): Promise<HealthResponse | null> {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            return await response.json();
        } catch {
            return null;
        }
    }

    async isBackendRunning(): Promise<boolean> {
        const health = await this.checkHealth();
        return health?.status === 'ok';
    }

    async startWakeWord(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/wake-word/start`, {
                method: 'POST'
            });
            const data = await response.json();
            return data.status === 'started' || data.status === 'already_listening';
        } catch (error) {
            console.error('Failed to start wake word:', error);
            return false;
        }
    }

    async stopWakeWord(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/wake-word/stop`, {
                method: 'POST'
            });
            const data = await response.json();
            return data.status === 'stopped';
        } catch (error) {
            console.error('Failed to stop wake word:', error);
            return false;
        }
    }

    async pollWakeWord(): Promise<{ detected: boolean; keyword?: string }> {
        try {
            const response = await fetch(`${this.baseUrl}/wake-word/poll`);
            return await response.json();
        } catch {
            return { detected: false };
        }
    }

    async recordAudio(options?: {
        maxDuration?: number;
        silenceThreshold?: number;
        silenceDuration?: number;
    }): Promise<RecordResponse> {
        try {
            const response = await fetch(`${this.baseUrl}/audio/record`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    max_duration: options?.maxDuration ?? 10,
                    silence_threshold: options?.silenceThreshold ?? 500,
                    silence_duration: options?.silenceDuration ?? 1.5
                })
            });
            return await response.json();
        } catch (error) {
            return { audio_path: '', audio_base64: '', success: false, error: String(error) };
        }
    }

    async transcribe(audioBase64: string): Promise<TranscribeResponse> {
        try {
            const response = await fetch(`${this.baseUrl}/stt/transcribe`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ audio_base64: audioBase64 })
            });
            return await response.json();
        } catch (error) {
            return { text: '', success: false, error: String(error) };
        }
    }

    async speak(text: string, voice: 'male' | 'female' = 'male', play: boolean = true): Promise<TTSResponse> {
        try {
            const response = await fetch(`${this.baseUrl}/tts/speak`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, voice, play })
            });
            return await response.json();
        } catch (error) {
            return { audio_path: '', success: false, error: String(error) };
        }
    }

    async getVoices(): Promise<{ id: string; name: string; description: string }[]> {
        try {
            const response = await fetch(`${this.baseUrl}/tts/voices`);
            const data = await response.json();
            return data.voices || [];
        } catch {
            return [];
        }
    }

    async setVoice(voice: 'male' | 'female'): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/tts/set-voice`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ voice })
            });
            const data = await response.json();
            return data.success;
        } catch {
            return false;
        }
    }
}

export const pythonBridge = new PythonBridge();
export default pythonBridge;
