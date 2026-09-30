import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal

class AudioListenerWorker(QThread):
    text_recognized = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, language="fr-FR"):
        super().__init__()
        self.language = language

    def run(self):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                # Ajustement automatique au bruit ambiant
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                # Écoute du micro
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
                
                # Transcription via l'API Google Speech
                text = recognizer.recognize_google(audio, language=self.language)
                if text:
                    self.text_recognized.emit(text)
        except sr.WaitTimeoutError:
            self.error_occurred.emit("Temps d'écoute dépassé (aucun son détecté).")
        except sr.UnknownValueError:
            self.error_occurred.emit("Impossible de comprendre l'audio.")
        except Exception as e:
            self.error_occurred.emit(f"Erreur micro : {str(e)}")