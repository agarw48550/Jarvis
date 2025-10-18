import os
import struct
import pvporcupine
import pyaudio


def listen_for_wake_word():
    """Simple wake-word listener that hands off to Jarvis active interaction.
    Reads PICOVOICE_ACCESS_KEY from environment and uses the built-in 'jarvis' keyword.
    """
    access_key = os.getenv("PICOVOICE_ACCESS_KEY", "").strip()
    if not access_key:
        print("PICOVOICE_ACCESS_KEY is not set; wake word disabled.")
        return

    porcupine = None
    pa = None
    audio_stream = None
    try:
        porcupine = pvporcupine.create(access_key=access_key, keywords=["jarvis"])
        pa = pyaudio.PyAudio()
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length,
        )
        print("✅ Jarvis is on standby. Listening for 'Jarvis'…")

        # Lazy imports to avoid heavy deps if unused
        from agent.core import ChatSession
        from jarvis import active_interaction, stop_speaking

        while True:
            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            idx = porcupine.process(pcm)
            if idx >= 0:
                print("Wake word detected!")
                try:
                    stop_speaking()
                except Exception:
                    pass
                try:
                    active_interaction(ChatSession())
                except Exception as e:
                    print(f"[wakeword] error entering interaction: {e}")
                print("✅ Returning to standby…")
    except KeyboardInterrupt:
        print("Stopping wake word detector.")
    finally:
        try:
            if audio_stream:
                audio_stream.close()
        except Exception:
            pass
        try:
            if pa:
                pa.terminate()
        except Exception:
            pass
        try:
            if porcupine:
                porcupine.delete()
        except Exception:
            pass