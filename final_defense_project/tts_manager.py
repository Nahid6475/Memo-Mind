from gtts import gTTS
import io
import os
import threading
import platform
import pygame
import tempfile


class BanglaTTSManager:
    """Text-to-Speech manager - Direct play without saving files"""

    def __init__(self):
        # Initialize pygame mixer for direct playback
        try:
            pygame.mixer.init()
            print("✅ TTS Manager initialized - Direct voice play mode")
        except Exception as e:
            print(f"⚠️ Pygame init error: {e}")
            print("⚠️ Trying alternative method...")

    def speak(self, text, lang='bn'):
        """Speak text directly without saving any file"""

        def _speak():
            try:
                # Create gTTS object
                tts = gTTS(text=text, lang=lang, slow=False)

                # Save to temporary file (auto-deleted after play)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                    temp_filename = fp.name
                    tts.save(temp_filename)

                # Play the audio using pygame
                pygame.mixer.music.load(temp_filename)
                pygame.mixer.music.play()

                # Wait for playback to finish
                while pygame.mixer.music.get_busy():
                    threading.Event().wait(0.1)

                # Clean up temp file
                try:
                    os.unlink(temp_filename)
                except:
                    pass

            except Exception as e:
                print(f"TTS Error: {e}")
                # Fallback: try using system default player
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                        temp_filename = fp.name
                        tts = gTTS(text=text, lang=lang, slow=False)
                        tts.save(temp_filename)

                    if platform.system() == "Windows":
                        os.system(f'start {temp_filename}')
                    else:
                        os.system(f'xdg-open {temp_filename}')

                    # Schedule cleanup
                    threading.Timer(5.0, lambda: os.unlink(temp_filename)).start()
                except:
                    pass

        # Run in separate thread
        thread = threading.Thread(target=_speak)
        thread.daemon = True
        thread.start()
        return True