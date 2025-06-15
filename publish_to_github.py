import subprocess
import os

def publish_page(filepath):
    # Datei ins Hauptverzeichnis kopieren
    filename = os.path.basename(filepath)
    os.replace(filepath, filename)

    subprocess.run(["git", "add", filename])
    subprocess.run(["git", "commit", "-m", f"Add page: {filename}"])
    subprocess.run(["git", "push", "origin", "main"])
