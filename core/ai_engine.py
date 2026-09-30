import os
import time
from dotenv import load_dotenv
from google import genai
from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image

load_dotenv()

class GeminiWorker(QThread):
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, prompt: str, chat_history: list = None, image_path: str = None):
        super().__init__()
        self.prompt = prompt
        self.chat_history = chat_history or []
        self.image_path = image_path
        self.api_key = os.getenv("GEMINI_API_KEY")

    def run(self):
        if not self.api_key:
            self.error_occurred.emit("Clé GEMINI_API_KEY introuvable dans le .env !")
            return

        try:
            start_time = time.time()
            client = genai.Client(api_key=self.api_key)
            
            # Format minimaliste et direct pour maximiser la vitesse
            contents = []
            if self.chat_history:
                for msg in self.chat_history[-2:]:
                    contents.append(f"{msg['role']}: {msg['content']}")

            if self.image_path and os.path.exists(self.image_path):
                try:
                    img = Image.open(self.image_path)
                    contents.append(img)
                except Exception:
                    pass

            contents.append(f"Utilisateur : {self.prompt}")

            # Appel direct au modèle sans configuration lourde de system instruction
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents
            )
            
            elapsed = time.time() - start_time
            print(f"⚡ Temps de réponse : {elapsed:.2f} secondes")

            if response and response.text:
                self.response_received.emit(response.text.strip())
            else:
                self.error_occurred.emit("Réponse vide de l'API.")
                
        except Exception as e:
            # Si le modèle 2.5-flash pose problème, on bascule direct sur une alternative dans l'exception
            try:
                client = genai.Client(api_key=self.api_key)
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=contents
                )
                if response and response.text:
                    self.response_received.emit(response.text.strip())
                    return
            except Exception as inner_e:
                pass
                
            self.error_occurred.emit(f"Erreur : {str(e)}")