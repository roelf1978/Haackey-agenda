import asyncio
from pyppeteer import launch
from datetime import datetime
import os

async def scrape_wedstrijdschema():
    # Browser lanceren met extra argumenten
    print("[INFO] Browser starten...")
    browser = await launch(
        headless=True,  # Je kunt dit naar False veranderen voor debugging
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
    )
    page = await browser.newPage()
    
    try:
        # User-agent aanpassen
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
        
        # Pagina openen
        print("[INFO] Pagina openen...")
        await page.goto('https://www.haackey.nl/wedstrijdschema', waitUntil='networkidle2')
        
        # Even wachten voor de pagina volledig is geladen
        await asyncio.sleep(5)
        
        # Probeer cookies te accepteren indien nodig (pas de selector aan)
        try:
            await page.waitForSelector('.cookie-button', timeout=10000)  # Verhoogde timeout
            await page.click('.cookie-button')  # Vervang met juiste selector
            print("[INFO] Cookie banner weggeklikt")
        except Exception as e:
            print("[INFO] Geen cookie banner gevonden of andere fout:", e)
        
        # Screenshot maken om te zien wat de scraper ziet
        print("[DEBUG] Screenshot maken voor debug...")
        await page.screenshot({'path': 'screenshot_wedstrijdschema.png', 'fullPage': True})
        
        # Wachten op wedstrijdschema-selector
        print("[INFO] Wachten op wedstrijdschema-selector...")
        await page.waitForSelector('.home-team', timeout=60000)  # Verhoogde timeout
        
        # Data scrapen
        print("[INFO] Wedstrijdschema laden...")
        matches = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.single-item')).map(el => {
                return {
                    home_team: el.querySelector('.home-team')?.innerText.trim(),
                    away_team: el.querySelector('.away-team')?.innerText.trim(),
                    time: el.querySelector('.main-time')?.innerText.trim(),
                    field: el.querySelector('.play-field')?.innerText.trim()
                };
            });
        }''')
        
 # HTML genereren
        html = f"""
        <html>
        <head>
            <meta charset='UTF-8'>
            <meta name='viewport' content='width=device-width, initial-scale=1.0'>
            <style>
                body {{
                    font-family: sans-serif;
                    color: #fff;
                    background-color: #003366;
                    text-align: center;
                    margin: 0;
                    padding: 20px;
                }}
                .slide {{
                    padding: 1vw;
                }}
                h2 {{
                    font-size: clamp(24px, 5vw, 60px);
                    margin-bottom: 20px;
                }}
                li {{
                    font-size: clamp(16px, 2.5vw, 32px);
                    margin: 10px 0;
                }}
                ul {{
                    list-style-type: none;
                    padding: 0;
                }}
            </style>
        </head>
        <body>
        <div class="slide">
        <h2>Wedstrijdschema - HHC Haackey ({datetime.now().strftime('%d-%m-%Y')})</h2>
        <ul>
        """
        for match in matches:
            html += f"<li><strong><h2>{match['home_team']} vs {match['away_team']}</strong> - Tijd: {match['time']}, Veld: {match['field']}</h2></li>"
        html += "</ul></div></body></html>"
        
        # Controleer of de map 'public' bestaat
        output_dir = "public"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # HTML opslaan
        output_file = os.path.join(output_dir, "wedstrijdschema.html")
        with open(output_file, "w") as f:
            f.write(html)
        print(f"[INFO] Wedstrijdschema opgeslagen in {output_file}")
    except Exception as e:
        print(f"[FOUT] Er is een fout opgetreden: {e}")
    finally:
        # Browser sluiten
        await browser.close()

# Asynchrone hoofdfunctie uitvoeren voor de scraper
asyncio.run(scrape_wedstrijdschema())
