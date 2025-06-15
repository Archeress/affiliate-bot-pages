import subprocess
from generate_article import generate_article
from create_page import create_html_page
from publish_to_github import publish_page

# Beispielprodukt (später dynamisch erweiterbar)
product = {
    "title": "Online Hundetraining",
    "link": "https://www.digistore24.com/redir/123456/DEINUSERNAME/",
    "description": "Ein umfassendes Videotraining zur Hundeerziehung für Anfänger und Fortgeschrittene."
}

print("🔄 Artikel wird generiert...")
article = generate_article(product)

print("🧱 HTML-Seite wird erstellt...")
filename = create_html_page(product, article)

print("🚀 Seite wird auf GitHub veröffentlicht...")
publish_page(filename)
