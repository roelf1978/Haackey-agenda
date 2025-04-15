import asyncio
from pyppeteer import launch
from datetime import datetime
import os

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
            # Parse datum en negeer tijd
            parsed_date = datetime.strptime(event['date'], "%d-%m-%Y, %H:%M")
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
            <style>
                body {
                    font-family: sans-serif;
                    
                    color: #fff;
                    text-align: center;
                }
                h2 {
                    font-size: 24px;
                    margin-bottom: 20px;
                }
                h3 {
                    font-size: 20px;
                    margin-top: 30px;
                }
                ul {
                    list-style-type: none;
                    padding: 0;
                }
                li {
                    margin: 10px 0;
                }
            </style>
        </head>
        <body>
        """
        html += f"<h2>Agenda - HHC Haackey ({datetime.now().strftime('%d-%m-%Y')})</h2>"
        for month, events in grouped_events.items():
            html += f"<h3>{month}</h3><ul>"
            for event in events:
                html += f"<li><strong>{event['date']}</strong>: {event['title']}</li>"
            html += "</ul>"
        html += "</body></html>"
        
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
