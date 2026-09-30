# Nova - Assistant Virtuel de Bureau (PyQt6)

Nova est un assistant de bureau minimaliste, toujours au premier plan, développé en Python avec PyQt6. Il intègre une interface flottante moderne, des raccourcis clavier, la capture d'écran rapide (`mss`) et la reconnaissance vocale.

## Fonctionnalités
* **Interface minimale et flottante :** Widget transparent et toujours au premier plan.
* **Commandes vocales :** Déclenchement par bouton micro (`SpeechRecognition`).
* **Capture d'écran intégrée :** Permet d'analyser l'écran à la volée.
* **Moteur IA :** Intégration de l'API Gemini pour des réponses textuelles rapides.

## Installation

1. Clone le dépôt :
   ```bash
   git clone [https://github.com/OxanasXO7/nova-desktop-assistant.git](https://github.com/OxanasXO7/nova-desktop-assistant.git)
   cd nova-desktop-assistant
Installe les dépendances requises :

Bash
pip install -r requirements.txt
Configure ta clé API :

2-Crée un fichier nommé .env à la racine du projet.

3-Ajoute ta clé dedans :

Extrait de code
GEMINI_API_KEY=ta_cle_api_ici

4-Lance l'application :

Bash
python main.py
