import os
import requests
import time
import json
from datetime import datetime
import re
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys

# Konfiguration
CONFIG = {
    "digistore_username": "Archeress",
    "lm_studio_url": "http://localhost:1234/v1",
    "images_dir": "images",
    "pages_dir": "pages",
    "github_repo": "affiliate-bot-pages",
    "pixabay_api_key": "50476472-732b17fe8d841cd223e62eaf6",
    "max_products": 20,
    "min_commission": 30,
    "cookie_file": "digistore_cookies.json"
}

class Digistore24CookieScraper:
    """Nutzt exportierte Cookies für Digistore24"""
    
    def __init__(self):
        self.setup_driver()
        self.products = []
    
    def setup_driver(self):
        """Chrome Setup"""
        chrome_options = Options()
        # chrome_options.add_argument('--headless')  # Deaktiviert für Debugging
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("✅ Chrome gestartet (sichtbar für Debugging)")
    
    def load_cookies_and_login(self):
        """Lädt Cookies aus JSON und loggt ein"""
        try:
            # Gehe erst zur Hauptseite
            print("🍪 Lade Cookies...")
            self.driver.get("https://www.digistore24-app.com/app/de/affiliate/account/marketplace/all")
            time.sleep(2)
            
            # Lade Cookies aus JSON
            with open(CONFIG["cookie_file"], 'r') as f:
                cookies = json.load(f)
            
            # Füge jeden Cookie hinzu
            for cookie in cookies:
                # Bereite Cookie für Selenium vor
                cookie_dict = {
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    'domain': cookie.get('domain', '.digistore24.com'),
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', True)
                }
                
                # Entferne None-Werte
                cookie_dict = {k: v for k, v in cookie_dict.items() if v is not None}
                
                try:
                    self.driver.add_cookie(cookie_dict)
                except Exception as e:
                    print(f"   ⚠️ Cookie konnte nicht hinzugefügt werden: {cookie.get('name')}")
            
            print("✅ Cookies geladen")
            
            # Teste ob eingeloggt
            self.driver.get("https://www.digistore24.com/marketplace")
            time.sleep(3)
            
            # Prüfe URL
            if "login" in self.driver.current_url:
                print("❌ Login fehlgeschlagen - Cookies abgelaufen?")
                return False
            else:
                print("✅ Erfolgreich eingeloggt!")
                return True
                
        except Exception as e:
            print(f"❌ Fehler beim Cookie-Login: {e}")
            return False
    
    def scrape_products(self):
        """Scrapt Produkte vom Marktplatz"""
        products = []
        
        try:
            print("📦 Hole Affiliate-Produkte...")
            
            # Gehe zum Marktplatz mit der richtigen URL
            self.driver.get("https://www.digistore24-app.com/app/de/affiliate/account/marketplace/all")
            time.sleep(5)
            
            # Warte bis Seite geladen ist
            wait = WebDriverWait(self.driver, 15)
            
            # Scrolle und sammle Produkte
            scroll_attempts = 0
            processed_buttons = set()  # Um Duplikate zu vermeiden
            
            while scroll_attempts < 5 and len(products) < CONFIG["max_products"]:
                # Finde alle "Jetzt promoten" Buttons
                promo_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Jetzt promoten')]")
                
                print(f"   📦 {len(promo_buttons)} Produkte auf der Seite")
                
                # Verarbeite neue Buttons
                for button in promo_buttons:
                    if len(products) >= CONFIG["max_products"]:
                        break
                    
                    # Skip wenn bereits verarbeitet
                    button_id = id(button)
                    if button_id in processed_buttons:
                        continue
                    processed_buttons.add(button_id)
                    
                    try:
                        # Finde die Produktkarte
                        card = button.find_element(By.XPATH, "./ancestor::div[contains(@style, 'border-radius')]")
                        
                        # Prüfe vorab auf Mindestprovision (wenn möglich)
                        card_text = card.text
                        commission_match = re.search(r'([\d,]+(?:,\d+)?)\s*%', card_text)
                        if commission_match:
                            commission = float(commission_match.group(1).replace(',', '.'))
                            if commission < CONFIG["min_commission"]:
                                print(f"   ⏭️ Überspringe Produkt mit nur {commission}% Provision")
                                continue
                        
                        # Scrolle zum Element
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", card)
                        time.sleep(0.5)
                        
                        # Extrahiere Produktinfos
                        product = self.extract_product_from_card_v2(card, button)
                        
                        if product and product['commission'] >= CONFIG["min_commission"]:
                            products.append(product)
                            print(f"   ✅ {product['name']} - {product['price']}€ ({product['commission']}%)")
                            
                    except Exception as e:
                        print(f"   ⚠️ Fehler bei Produkt: {str(e)[:50]}")
                        continue
                
                # Scrolle weiter nach unten
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                scroll_attempts += 1
                print(f"   📜 Scrolle weiter... (Versuch {scroll_attempts}/5)")
            
            if not products:
                print("   ⚠️ Keine Produkte gefunden - nutze Beispielprodukte")
                return self.get_sample_products()
            
            print(f"\n✅ {len(products)} Produkte mit ≥{CONFIG['min_commission']}% Provision gesammelt!")
            return products
            
        except Exception as e:
            print(f"❌ Fehler beim Scraping: {e}")
            self.driver.save_screenshot("scraping_error.png")
            print("   📸 Screenshot gespeichert als scraping_error.png")
            print("   ⚠️ Nutze Beispielprodukte als Fallback...")
            return self.get_sample_products()
    
    def extract_product_from_card_v2(self, card, button):
        """Extrahiert Infos aus einer Produktkarte V2"""
        try:
            # Hole zuerst die Basis-Infos aus der Karte
            card_text = card.text
            lines = [line.strip() for line in card_text.split('\n') if line.strip()]
            
            # Produktname - normalerweise die erste größere Textzeile
            name = ""
            for line in lines:
                if len(line) > 20 and not any(x in line for x in ['€', '%', 'Verkaufsseite', 'Support', 'Jetzt promoten']):
                    name = line
                    break
            
            if not name:
                name = lines[0] if lines else "Unbekanntes Produkt"
            
            # Preis - suche nach € Symbol
            price = "0"
            for line in lines:
                price_match = re.search(r'([\d,]+(?:,\d{2})?)\s*€', line)
                if price_match:
                    price = price_match.group(1).replace(',', '.')
                    break
            
            # Provision - suche nach % Symbol
            commission = 0
            for line in lines:
                if '%' in line and 'provision' not in line.lower():
                    commission_match = re.search(r'([\d,]+(?:,\d+)?)\s*%', line)
                    if commission_match:
                        commission = float(commission_match.group(1).replace(',', '.'))
                        break
            
            # Verkäufer/Vendor
            vendor = "Premium Vendor"
            vendor_keywords = ['Life:', 'mit', 'von', '|']
            for i, line in enumerate(lines):
                for keyword in vendor_keywords:
                    if keyword in line and i > 0:
                        # Vendor ist oft die Zeile davor
                        potential_vendor = lines[i-1]
                        if len(potential_vendor) < 50 and potential_vendor != name:
                            vendor = potential_vendor
                            break
            
            # Klicke auf "Jetzt promoten" um den Promolink zu bekommen
            product_id = "unknown"
            promo_link = ""
            
            try:
                # Scrolle zum Button und klicke
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                time.sleep(1)
                
                # Klicke den Button
                self.driver.execute_script("arguments[0].click();", button)
                time.sleep(2)
                
                # Warte auf das Modal
                wait = WebDriverWait(self.driver, 10)
                
                # Finde das Promolink Input-Feld
                promo_input = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@value, 'digistore24.com/redir/')]"))
                )
                
                # Hole den Promolink
                promo_link = promo_input.get_attribute("value")
                print(f"      → Promolink gefunden: {promo_link}")
                
                # Extrahiere Produkt-ID aus dem Link
                id_match = re.search(r'/redir/(\d+)/', promo_link)
                if id_match:
                    product_id = id_match.group(1)
                
                # Schließe das Modal - suche nach X oder Schließen-Button
                try:
                    # Versuche verschiedene Möglichkeiten das Modal zu schließen
                    close_selectors = [
                        "//button[contains(@class, 'close')]",
                        "//button[contains(text(), '×')]",
                        "//button[contains(text(), 'Schließen')]",
                        "//div[contains(@class, 'modal')]//button[contains(@class, 'btn-close')]",
                        "//*[@aria-label='Close' or @aria-label='Schließen']"
                    ]
                    
                    for selector in close_selectors:
                        try:
                            close_btn = self.driver.find_element(By.XPATH, selector)
                            close_btn.click()
                            time.sleep(0.5)
                            break
                        except:
                            continue
                    
                    # Fallback: ESC drücken
                    from selenium.webdriver.common.keys import Keys
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    
                except Exception as e:
                    print(f"      ⚠️ Modal konnte nicht geschlossen werden: {str(e)[:30]}")
                    # Versuche Seite neu zu laden als letzten Ausweg
                    # self.driver.refresh()
                    # time.sleep(2)
                    
            except Exception as e:
                print(f"      ⚠️ Konnte Promolink nicht abrufen: {str(e)[:50]}")
                # Generiere Fallback-Link
                promo_link = f"https://www.digistore24.com/redir/{product_id}/{CONFIG['digistore_username']}/"
            
            # Nur Produkte mit gültiger ID zurückgeben
            if product_id == "unknown":
                return None
            
            return {
                'id': product_id,
                'name': name[:100],
                'price': price,
                'commission': commission,
                'vendor': vendor,
                'category': 'Digital Product',
                'description': f"{name} von {vendor}",
                'promo_link': promo_link if promo_link else f"https://www.digistore24.com/redir/{product_id}/{CONFIG['digistore_username']}/"
            }
            
        except Exception as e:
            print(f"      ⚠️ Fehler beim Extrahieren: {str(e)[:50]}")
            return None
    
    def get_sample_products(self):
        """Beispiel-Produkte als Fallback - basierend auf deinem Screenshot"""
        return [
            {
                'id': '475177',  # KlickTipp ID aus Screenshot
                'name': 'Das Partnerprogramm von KlickTipp',
                'price': '475.10',
                'commission': 25,
                'vendor': 'KlickTipp',
                'category': 'E-Mail Marketing',
                'description': 'Das Beste oder nichts - Premium E-Mail Marketing Software',
                'promo_link': f"https://www.digistore24.com/redir/475177/{CONFIG['digistore_username']}/"
            },
            {
                'id': '413751',  # FunnelCockpit ID
                'name': 'FunnelCockpit - Die All-In-One Marketing Software',
                'price': '206.30',
                'commission': 25,
                'vendor': 'FunnelCockpit',
                'category': 'Marketing Software',
                'description': 'All-In-One Marketing Software für erfolgreiche Funnels',
                'promo_link': f"https://www.digistore24.com/redir/413751/{CONFIG['digistore_username']}/"
            },
            {
                'id': '176981',  # Feminin Bundle ID
                'name': 'Feminin Bundle - Die eigene Weiblichkeit erwecken',
                'price': '62.62',
                'commission': 30,
                'vendor': 'Energetic Family',
                'category': 'Persönlichkeitsentwicklung',
                'description': 'Downloads zur Erweckung der eigenen Weiblichkeit',
                'promo_link': f"https://www.digistore24.com/redir/176981/{CONFIG['digistore_username']}/"
            },
            {
                'id': '448839',
                'name': 'Cashcow 2.0 - Online Business Komplettpaket',
                'price': '499.00',
                'commission': 50,
                'vendor': 'Eric Promm',
                'category': 'Online Marketing',
                'description': 'Das ultimative Online Business System für passives Einkommen',
                'promo_link': f"https://www.digistore24.com/redir/448839/{CONFIG['digistore_username']}/"
            },
            {
                'id': '302188',
                'name': 'Vertriebsoffensive - Premium Sales Training',
                'price': '697.00',
                'commission': 40,
                'vendor': 'Dirk Kreuter',
                'category': 'Vertrieb & Sales',
                'description': 'Die beste Vertriebsausbildung im deutschsprachigen Raum',
                'promo_link': f"https://www.digistore24.com/redir/302188/{CONFIG['digistore_username']}/"
            }
        ]
    
    def close(self):
        """Schließt Browser"""
        self.driver.quit()


class LMStudioContentGenerator:
    """Content Generator"""
    
    def __init__(self):
        self.api_url = CONFIG["lm_studio_url"]
        print(f"🤖 LM Studio API: {self.api_url}")
    
    def generate_content(self, product):
        """Generiert Content für Produkt"""
        
        prompt = f"""Schreibe überzeugenden Verkaufstext für:
{product['name']}
Preis: {product['price']}€
Provision: {product['commission']}%

Erstelle:
1. Packende Headline
2. Einleitung (2-3 Sätze)
3. 3 Vorteile
4. Call-to-Action

Nutze Emojis und sei überzeugend!"""
        
        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 600
                },
                timeout=20
            )
            
            if response.status_code == 200:
                text = response.json()['choices'][0]['message']['content']
                return self._parse_response(text, product)
        except:
            pass
        
        return self._fallback_content(product)
    
    def _parse_response(self, text, product):
        """Parsed LLM Response"""
        lines = text.strip().split('\n')
        
        # Versuche strukturierte Antwort zu finden
        headline = next((l for l in lines if l.strip() and not l.startswith(('1.', '2.', '3.'))), 
                        f"🔥 {product['name']} - Jetzt {product['commission']}% sparen!")
        
        # Finde Einleitung
        intro_lines = []
        for i, line in enumerate(lines[1:], 1):
            if line.strip() and not line.startswith(('1.', '2.', '3.', '-', '•', '*')):
                intro_lines.append(line)
                if len(intro_lines) >= 2:
                    break
        intro = ' '.join(intro_lines) or self._fallback_intro(product)
        
        # Finde Vorteile
        benefits = []
        for line in lines:
            if line.strip().startswith(('✓', '•', '-', '*', '✅')):
                benefits.append(line.strip())
        
        if len(benefits) < 3:
            benefits = self._fallback_benefits(product)
        
        # CTA
        cta = lines[-1] if lines and '!' in lines[-1] else "Sichere dir jetzt dieses Top-Angebot! 💰"
        
        return {
            'headline': headline,
            'intro': intro,
            'benefits': benefits[:3],
            'cta': cta
        }
    
    def _fallback_content(self, product):
        return {
            'headline': f"🚀 {product['name']} - Spare {product['commission']}%!",
            'intro': self._fallback_intro(product),
            'benefits': self._fallback_benefits(product),
            'cta': "Jetzt zugreifen und massiv sparen! 💰"
        }
    
    def _fallback_intro(self, product):
        return f"""Entdecke {product['name']} zum absoluten Bestpreis! 
        Mit {product['commission']}% Rabatt sicherst du dir jetzt ein unschlagbares Angebot."""
    
    def _fallback_benefits(self, product):
        return [
            f"✅ Spare {product['commission']}% vom regulären Preis",
            f"✅ Premium {product['category']}-Lösung von {product['vendor']}",
            "✅ Sofortiger Zugang + 30 Tage Geld-zurück-Garantie"
        ]


class AffiliatePageGenerator:
    """Hauptklasse"""
    
    def __init__(self):
        self.scraper = Digistore24CookieScraper()
        self.content_gen = LMStudioContentGenerator()
        self.setup_dirs()
    
    def setup_dirs(self):
        for d in [CONFIG["images_dir"], CONFIG["pages_dir"]]:
            os.makedirs(d, exist_ok=True)
    
    def run(self):
        """Hauptprozess"""
        print("\n🚀 Starte Digistore24 Affiliate Automation\n")
        
        # Login mit Cookies
        if not self.scraper.load_cookies_and_login():
            print("❌ Cookie-Login fehlgeschlagen!")
            print("   Tipp: Exportiere die Cookies erneut")
            self.scraper.close()
            return
        
        # Hole Produkte
        products = self.scraper.scrape_products()
        
        if not products:
            print("❌ Keine Produkte gefunden!")
            self.scraper.close()
            return
        
        # Generiere Seiten
        generated = []
        for i, product in enumerate(products, 1):
            print(f"\n📝 [{i}/{len(products)}] {product['name']}")
            
            # Content generieren
            content = self.content_gen.generate_content(product)
            
            # HTML erstellen
            html_file = self.create_html_page(product, content)
            if html_file:
                generated.append(html_file)
                print(f"   ✅ Erstellt: {html_file}")
            
            time.sleep(1)
        
        # Index erstellen
        if generated:
            self.create_index_page(products)
            self.create_sitemap()
            print(f"\n✅ {len(generated)} Seiten erstellt!")
            
            # GitHub Push
            self.push_to_github()
        
        # Aufräumen
        self.scraper.close()
        
        print(f"\n✨ Fertig! Besuche: https://archeress.github.io/{CONFIG['github_repo']}/")
    
    def create_html_page(self, product, content):
        """Erstellt HTML Seite"""
        html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{content['headline']}</title>
    <meta name="description" content="{content['intro'][:150]}...">
    <style>
        :root {{
            --primary: #5D4E99;
            --secondary: #FF6B6B;
            --success: #4ECDC4;
            --dark: #2B2D42;
            --light: #F8F9FA;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--dark);
            background: var(--light);
        }}
        
        .hero {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 80px 20px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        
        .hero::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            animation: pulse 15s ease-in-out infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1) rotate(0deg); }}
            50% {{ transform: scale(1.1) rotate(180deg); }}
        }}
        
        .hero h1 {{
            font-size: 3em;
            margin-bottom: 20px;
            position: relative;
            z-index: 1;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .container {{
            max-width: 900px;
            margin: -40px auto 40px;
            background: white;
            padding: 50px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            position: relative;
            z-index: 2;
        }}
        
        .price-section {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            margin: 40px 0;
            position: relative;
        }}
        
        .price {{
            font-size: 4em;
            font-weight: bold;
            color: var(--secondary);
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }}
        
        .savings {{
            display: inline-block;
            background: var(--success);
            color: white;
            padding: 10px 30px;
            border-radius: 30px;
            font-size: 1.2em;
            font-weight: bold;
            margin: 20px 0;
            box-shadow: 0 5px 15px rgba(78,205,196,0.3);
        }}
        
        .intro {{
            font-size: 1.3em;
            line-height: 1.8;
            color: #555;
            margin: 40px 0;
            text-align: center;
        }}
        
        .benefits {{
            margin: 50px 0;
        }}
        
        .benefits h2 {{
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 40px;
            color: var(--primary);
        }}
        
        .benefit-list {{
            list-style: none;
        }}
        
        .benefit-list li {{
            font-size: 1.3em;
            margin: 25px 0;
            padding: 25px;
            background: linear-gradient(to right, #f5f7fa 0%, transparent 100%);
            border-radius: 10px;
            position: relative;
            padding-left: 60px;
            transition: transform 0.3s;
        }}
        
        .benefit-list li:hover {{
            transform: translateX(10px);
        }}
        
        .benefit-list li::before {{
            content: "✅";
            position: absolute;
            left: 20px;
            font-size: 1.5em;
        }}
        
        .cta-section {{
            text-align: center;
            margin: 60px 0;
            padding: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            color: white;
        }}
        
        .cta-section h2 {{
            font-size: 2.5em;
            margin-bottom: 30px;
        }}
        
        .cta-button {{
            display: inline-block;
            background: white;
            color: var(--primary);
            padding: 20px 60px;
            font-size: 1.5em;
            text-decoration: none;
            border-radius: 50px;
            font-weight: bold;
            transition: all 0.3s;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        
        .cta-button:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.4);
        }}
        
        .guarantee {{
            background: #e8f8f5;
            border: 2px solid var(--success);
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            margin: 40px 0;
        }}
        
        .guarantee h3 {{
            color: var(--success);
            font-size: 1.8em;
            margin-bottom: 15px;
        }}
        
        .footer {{
            text-align: center;
            padding: 40px 20px;
            color: #999;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 30px 20px;
            }}
            
            .hero h1 {{
                font-size: 2em;
            }}
            
            .price {{
                font-size: 3em;
            }}
            
            .cta-button {{
                padding: 15px 40px;
                font-size: 1.2em;
            }}
        }}
    </style>
</head>
<body>
    <div class="hero">
        <h1>{content['headline']}</h1>
        <p style="font-size: 1.2em; opacity: 0.9;">🏷️ {product['category']} | 👤 {product['vendor']}</p>
    </div>
    
    <div class="container">
        <p class="intro">{content['intro']}</p>
        
        <div class="price-section">
            <div class="price">{product['price']}€</div>
            <div class="savings">🎉 Du sparst {product['commission']}%!</div>
            <p style="margin-top: 20px; color: #666;">Nur für kurze Zeit verfügbar!</p>
        </div>
        
        <div class="benefits">
            <h2>Was dich erwartet:</h2>
            <ul class="benefit-list">
                {''.join([f'<li>{benefit}</li>' for benefit in content['benefits']])}
            </ul>
        </div>
        
        <div class="cta-section">
            <h2>{content['cta']}</h2>
            <a href="{product['promo_link']}" class="cta-button" target="_blank">
                Jetzt sichern →
            </a>
        </div>
        
        <div class="guarantee">
            <h3>🛡️ 100% Zufriedenheitsgarantie</h3>
            <p>30 Tage Geld-zurück-Garantie - ohne Wenn und Aber! Deine Zufriedenheit steht an erster Stelle.</p>
        </div>
    </div>
    
    <div class="footer">
        <p>* Dies ist ein Affiliate-Link. Beim Kauf über diesen Link erhalten wir eine kleine Provision.</p>
        <p>Der Preis bleibt für dich natürlich gleich. Vielen Dank für deine Unterstützung!</p>
    </div>
</body>
</html>"""
        
        # Speichern
        filename = re.sub(r'[^\w\s-]', '', product['name'].lower())
        filename = re.sub(r'[-\s]+', '-', filename)[:40]
        filepath = os.path.join(CONFIG["pages_dir"], f"{filename}-{product['id']}.html")
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)
            return filepath
        except:
            return None
    
    def create_index_page(self, products):
        """Erstellt Index"""
        html = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💰 Top Affiliate Deals - Spare bis zu 75%!</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            margin: 0;
            padding: 0;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 20px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 3em;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.3em;
            margin-top: 20px;
            opacity: 0.9;
        }
        
        .container {
            max-width: 1200px;
            margin: -40px auto 40px;
            padding: 0 20px;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 30px;
            margin-top: 60px;
        }
        
        .card {
            background: white;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: all 0.3s;
            position: relative;
        }
        
        .card:hover {
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
        }
        
        .card-header {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            position: relative;
        }
        
        .commission-badge {
            position: absolute;
            top: 20px;
            right: 20px;
            background: #FF6B6B;
            color: white;
            padding: 8px 20px;
            border-radius: 30px;
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .card-body {
            padding: 30px;
        }
        
        .card h3 {
            margin: 0 0 15px 0;
            font-size: 1.5em;
            color: #2B2D42;
        }
        
        .card .meta {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 20px;
        }
        
        .card .price {
            font-size: 2.5em;
            color: #4ECDC4;
            font-weight: bold;
            margin: 20px 0;
        }
        
        .card .btn {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 40px;
            text-decoration: none;
            border-radius: 30px;
            font-weight: bold;
            transition: all 0.3s;
            width: 100%;
            text-align: center;
        }
        
        .card .btn:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 20px rgba(102,126,234,0.4);
        }
        
        .footer {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Premium Affiliate Deals</h1>
        <p>Spare bis zu 75% bei den besten Online-Produkten!</p>
    </div>
    
    <div class="container">
        <div class="grid">
"""
        
        for product in products:
            filename = re.sub(r'[^\w\s-]', '', product['name'].lower())
            filename = re.sub(r'[-\s]+', '-', filename)[:40]
            
            html += f"""
            <div class="card">
                <div class="card-header">
                    <span class="commission-badge">-{product['commission']}%</span>
                </div>
                <div class="card-body">
                    <h3>{product['name'][:50]}{'...' if len(product['name']) > 50 else ''}</h3>
                    <p class="meta">📦 {product['category']} | 👤 {product['vendor']}</p>
                    <div class="price">{product['price']}€</div>
                    <a href="{CONFIG['pages_dir']}/{filename}-{product['id']}.html" class="btn">
                        Zum Angebot →
                    </a>
                </div>
            </div>
"""
        
        html += """
        </div>
    </div>
    
    <div class="footer">
        <p>* Alle Preise inkl. MwSt. | Bei allen Links handelt es sich um Affiliate-Links.</p>
        <p>Beim Kauf über diese Links erhalten wir eine kleine Provision. Der Preis bleibt für dich gleich.</p>
    </div>
</body>
</html>"""
        
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html)
    
    def create_sitemap(self):
        """Erstellt Sitemap"""
        sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        # Index
        sitemap += f"""  <url>
    <loc>https://archeress.github.io/{CONFIG["github_repo"]}/</loc>
    <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""
        
        # Produktseiten
        for file in os.listdir(CONFIG["pages_dir"]):
            if file.endswith(".html"):
                sitemap += f"""  <url>
    <loc>https://archeress.github.io/{CONFIG["github_repo"]}/{CONFIG["pages_dir"]}/{file}</loc>
    <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>\n"""
        
        sitemap += '</urlset>'
        
        with open("sitemap.xml", "w", encoding="utf-8") as f:
            f.write(sitemap)
    
    def push_to_github(self):
        """Pusht zu GitHub"""
        try:
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", f"Update: {datetime.now().strftime('%d.%m.%Y %H:%M')}"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("\n✅ Erfolgreich zu GitHub gepusht!")
        except:
            print("\n⚠️ GitHub Push fehlgeschlagen - pushe manuell mit:")
            print("   git add .")
            print("   git commit -m 'Update'")
            print("   git push")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════╗
    ║   Digistore24 Automation mit Cookie JSON       ║
    ╚════════════════════════════════════════════════╝
    """)
    
    # Optionen
    print("\n🔧 Wähle eine Option:")
    print("1. Automatisches Scraping mit Cookies")
    print("2. Nutze Beispiel-Produkte (schneller)")
    
    choice = input("\nDeine Wahl (1 oder 2): ").strip()
    
    if choice == "2":
        # Schneller Modus mit Beispielprodukten
        print("\n⚡ Schnellmodus - nutze Beispielprodukte")
        
        # LM Studio Check
        try:
            response = requests.get(f"{CONFIG['lm_studio_url']}/models", timeout=5)
            if response.status_code == 200:
                print("✅ LM Studio läuft")
        except:
            print("⚠️ LM Studio nicht erreichbar - nutze Fallback-Texte")
        
        # Vereinfachter Generator ohne Selenium
        class QuickGenerator:
            def __init__(self):
                self.content_gen = LMStudioContentGenerator()
                self.setup_dirs()
                
            def setup_dirs(self):
                for d in [CONFIG["images_dir"], CONFIG["pages_dir"]]:
                    os.makedirs(d, exist_ok=True)
                    
            def run(self):
                scraper = Digistore24CookieScraper()
                products = scraper.get_sample_products()
                
                generated = []
                for i, product in enumerate(products, 1):
                    print(f"\n📝 [{i}/{len(products)}] {product['name']}")
                    content = self.content_gen.generate_content(product)
                    
                    generator = AffiliatePageGenerator()
                    html_file = generator.create_html_page(product, content)
                    if html_file:
                        generated.append(html_file)
                        print(f"   ✅ Erstellt: {html_file}")
                    time.sleep(1)
                
                if generated:
                    generator.create_index_page(products)
                    generator.create_sitemap()
                    generator.push_to_github()
                
                print(f"\n✨ Fertig! {len(generated)} Seiten erstellt.")
                print(f"🔗 https://archeress.github.io/{CONFIG['github_repo']}/")
        
        quick_gen = QuickGenerator()
        quick_gen.run()
        
    else:
        # Normaler Modus mit Cookies
        # Prüfe Cookie-Datei
        if not os.path.exists(CONFIG["cookie_file"]):
            print(f"❌ Cookie-Datei nicht gefunden: {CONFIG['cookie_file']}")
            print("\n📝 So exportierst du Cookies:")
            print("1. Installiere 'EditThisCookie' Chrome Extension")
            print("2. Gehe zu Digistore24 (eingeloggt)")
            print("3. Klicke auf Extension → Export → JSON")
            print("4. Speichere als 'digistore_cookies.json'")
            exit(1)
        
        # LM Studio Check
        try:
            response = requests.get(f"{CONFIG['lm_studio_url']}/models", timeout=5)
            if response.status_code == 200:
                print("✅ LM Studio läuft")
        except:
            print("⚠️ LM Studio nicht erreichbar - nutze Fallback-Texte")
        
        # Starte Automation
        generator = AffiliatePageGenerator()
        generator.run()
