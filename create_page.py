import os

def create_html_page(product, article_text):
    template = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <title>{product['title']}</title>
        <meta name="description" content="{product['description']}">
        <style>
            body {{ font-family: sans-serif; max-width: 700px; margin: auto; padding: 20px; }}
            .cta {{ background-color: #ff6600; color: white; padding: 10px 20px; display: inline-block; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>{product['title']}</h1>
        <p>{product['description']}</p>
        <hr>
        <article>{article_text.replace("\n", "<br>")}</article>
        <br><a href="{product['link']}" class="cta">Jetzt kaufen</a>
    </body>
    </html>
    """

    filename = product["title"].lower().replace(" ", "_") + ".html"
    filepath = f"articles/{filename}"

    os.makedirs("articles", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(template)

    return filepath
