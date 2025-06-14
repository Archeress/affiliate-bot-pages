import requests

def generate_article(product):
    prompt = (
        f"Schreibe einen SEO-optimierten Blogartikel über folgendes Produkt:\n\n"
        f"Titel: {product['title']}\n"
        f"Beschreibung: {product['description']}\n"
        f"Call-to-Action: Jetzt kaufen unter {product['link']}\n\n"
        f"Stil: informativ, überzeugend, für Einsteiger geeignet.\n\n"
    )

    response = requests.post("http://localhost:1234/v1/completions", json={
        "model": "local-model",  # z. B. "mistral" – je nach LM Studio Modell
        "prompt": prompt,
        "max_tokens": 700,
        "temperature": 0.7,
    })

    return response.json()["choices"][0]["text"].strip()
