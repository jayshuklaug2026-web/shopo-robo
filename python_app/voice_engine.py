"""
Shopo Robo - Thread-Safe SAPI Voice Engine for Windows
Uses native SAPI.SpVoice with SVSFlagsAsync for zero-blocking speech.
"""

import threading
import subprocess
import sys

class VoiceEngine:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.enabled = True
        self.volume = 100
        self.rate = 1
        self._sapi = None
        self._init_sapi()

    def _init_sapi(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
            import win32com.client
            self._sapi = win32com.client.Dispatch("SAPI.SpVoice")
            self._sapi.Volume = self.volume
            self._sapi.Rate = self.rate
        except Exception as e:
            print(f"[VoiceEngine] SAPI init: {e}")
            self._sapi = None

    def set_volume(self, vol: int):
        self.volume = max(0, min(100, vol))
        if self._sapi:
            try:
                self._sapi.Volume = self.volume
            except Exception:
                pass

    def set_rate(self, rate: int):
        self.rate = max(-5, min(5, rate))
        if self._sapi:
            try:
                self._sapi.Rate = self.rate
            except Exception:
                pass

    def speak(self, text: str):
        if not self.enabled or not text:
            return

        def _worker():
            try:
                import pythoncom
                pythoncom.CoInitialize()
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Volume = self.volume
                speaker.Rate = self.rate
                # 1 = SVSFlagsAsync
                speaker.Speak(text, 1)
            except Exception:
                # Fallback to PowerShell
                clean = text.replace('"', '""').replace("'", "''")
                cmd = f"Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('{clean}')"
                try:
                    subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                                   creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "windows" else 0,
                                   timeout=10)
                except Exception:
                    pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def stop(self):
        # Stop speaking if currently active
        pass
