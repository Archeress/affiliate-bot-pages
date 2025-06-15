import os

files = {
    "run_bot.py": '''
import bild_downloader
import generate_article
import create_page
import publish_to_github

def main():
    print("🔄 Artikel wird generiert...")
    article = generate_article.generate_article("Online Hundetraining")
    print("🧱 HTML-Seite wird erstellt...")
    image_url = bild_downloader.download_image("hundetraining")
    html_file = create_page.create_page(article, image_url, "archeress")
    print("🚀 Seite wird auf GitHub veröffentlicht...")
    publish_to_github.publish(html_file)

if __name__ == "__main__":
    main()
''',

    "bild_downloader.py": '''
import os
import requests

API_KEY = "50476472-732b17fe8d841cd223e62eaf6"
IMAGES_DIR = "images"

def download_image(query):
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)
    url = f"https://pixabay.com/api/?key={API_KEY}&q={query}&image_type=photo&per_page=3"
    response = requests.get(url)
    data = response.json()
    if data["hits"]:
        img_url = data["hits"][0]["webformatURL"]
        img_name = os.path.join(IMAGES_DIR, img_url.split("/")[-1])
        img_data = requests.get(img_url).content
        with open(img_name, "wb") as f:
            f.write(img_data)
        return img_name
    else:
        return ""

''',

    "generate_article.py": '''
def generate_article(topic):
    return f"""
<h1>{topic}</h1>
<p>Ein umfassendes Videotraining zur Hundeerziehung für Anfänger und Fortgeschrittene.</p>
<article>
Online Hundetraining: Die perfekte Lösung für Anfänger und Fortgeschrittene!<br><br>
Wenn du gerade einen neuen Hund hast, bist du hier richtig. Unser Online Hundetraining hilft dir dabei, deinem Hund die beste Erziehung zu geben.<br><br>
Klicke hier, um das Training zu kaufen: https://www.digistore24.com/redir/123456/archeress/
</article>
"""

''',

    "create_page.py": '''
def create_page(article, image_path, username):
    affiliate_link = f"https://www.digistore24.com/redir/123456/{username}/"
    html = f"""
<html>
<head><title>Affiliate Landingpage</title></head>
<body>
{article}
<img src="{image_path}" alt="Bild zum Thema" style="max-width:100%;">
<br>
<a href="{affiliate_link}" style="font-size:20px; color:green;">Jetzt kaufen</a>
</body>
</html>
"""
    filename = "online_hundetraining.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    return filename
''',

    "publish_to_github.py": '''
import os
import subprocess

def publish(filename):
    subprocess.run(["git", "add", filename])
    subprocess.run(["git", "commit", "-m", f"Add page: {filename}"])
    subprocess.run(["git", "push"])
''',
}

def create_files(base_dir="affiliate-bot"):
    if not os.path.exists(base_dir):
        os.mkdir(base_dir)
    for fname, content in files.items():
        path = os.path.join(base_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
    print(f"Alle Dateien wurden im Ordner '{base_dir}' erstellt.")

if __name__ == "__main__":
    create_files()
