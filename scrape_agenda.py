import asyncio
from pyppeteer import launch
from datetime import datetime
import os
import re

async def scrape():
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
        await page.goto('https://www.haackey.nl/agenda', waitUntil='networkidle2')
        
        # Even wachten voor de pagina volledig is geladen
        await asyncio.sleep(3)
        
        # Probeer cookies te accepteren indien nodig (pas de selector aan)
        try:
            await page.waitForSelector('.cookie-button', timeout=5000)  # Vervang met juiste selector
            await page.click('.cookie-button')  # Vervang met juiste selector
            print("[INFO] Cookie banner weggeklikt")
        except Exception as e:
            print("[INFO] Geen cookie banner gevonden of andere fout:", e)
        
        # Screenshot maken om te zien wat de scraper ziet
        print("[DEBUG] Screenshot maken voor debug...")
        await page.screenshot({'path': 'screenshot.png', 'fullPage': True})
        
        # Wachten op agenda-selector
        print("[INFO] Wachten op agenda-selector...")
        await page.waitForSelector('.clsLISAAgDate', timeout=30000)  # 30 seconden
        
        # Data scrapen
        print("[INFO] Agenda laden...")
        events = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.clsResultDiv')).map(el => {
                return {
                    date: el.querySelector('.clsLISAAgDate')?.innerText.trim(),
                    title: el.querySelector('.clsLISAAgTitle')?.innerText.trim()
                };
            });
        }''')
        
        # Groeperen op maand
        grouped_events = {}
        for event in events:
            if event['date']:
                try:
                    # Clean de datum (verwijder extra spaties rond de komma)
                    clean_date = re.sub(r'\s*,\s*', ', ', event['date'])
                    
                    # Parse datum
                    parsed_date = datetime.strptime(clean_date, "%d-%m-%Y, %H:%M")
                    month = parsed_date.strftime("%B %Y")
                    if month not in grouped_events:
                        grouped_events[month] = []
                    grouped_events[month].append(event)
                except Exception as e:
                    print(f"[FOUT] Fout bij het parseren van de datum: {event['date']} - {e}")
        
   # HTML genereren
        html = """
        <html>
        <head>
            <meta charset='UTF-8'>
            <meta name='viewport' content='width=device-width, initial-scale=1.0'>
            <style>
                body {
                    font-family: sans-serif;
                    color: #fff;
                    text-align: center;
                    background-color: #003366;
                }
                h2 {
                    font-size: clamp(24px, 5vw, 60px);
                }
                h3 {
                    font-size: clamp(20px, 4vw, 48px);
                }
                li {
                    font-size: clamp(16px, 2.5vw, 32px);
                    margin: 10px 0;
                }
                ul {
                    list-style-type: none;
                    padding: 0;
                }
            </style>
        </head>
        <body>
        <div class="slide">
        <h3>Agenda</h3>
        """

        for month, events_in_month in grouped_events.items():
            html += f"<h3>{month}</h3><ul>"
            for event in events_in_month:
                html += f"<li><strong><h2>{event['date']}</strong>: {event['title']}</h2></li>"
            html += "</ul>"

        html += "</div></body></html>"
        
        # Controleer of de map 'public' bestaat
        output_dir = "public"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # HTML opslaan
        output_file = os.path.join(output_dir, "agenda.html")
        with open(output_file, "w") as f:
            f.write(html)
        print(f"[INFO] Agenda opgeslagen in {output_file}")
    except Exception as e:
        print(f"[FOUT] Er is een fout opgetreden: {e}")
    finally:
        # Browser sluiten
        await browser.close()

# Asynchrone hoofdfunctie uitvoeren
asyncio.run(scrape())
