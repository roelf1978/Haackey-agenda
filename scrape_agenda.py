import asyncio
from pyppeteer import launch
from datetime import datetime
import os

async def scrape():
    # Browser lanceren
    print("[INFO] Browser starten...")
    browser = await launch(headless=True, args=['--no-sandbox'])
    async with browser:
        page = await browser.newPage()

        # Pagina openen
        print("[INFO] Pagina openen...")
        await page.goto('https://www.haackey.nl/agenda', waitUntil='networkidle2')

        # Wachten op agenda-selector
        try:
            print("[INFO] Wachten op agenda-selector...")
            await page.waitForSelector('.clsLISAAgDate', timeout=30000)  # 30 seconden
        except Exception as e:
            print("[FOUT] Agenda-element niet gevonden:", e)
            return

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

        # HTML genereren
        html = "<html><head><meta charset='UTF-8'><style>body{font-family:sans-serif;}</style></head><body>"
        html += f"<h2>Agenda - HHC Haackey ({datetime.now().strftime('%d-%m-%Y')})</h2><ul>"
        for event in events:
            html += f"<li><strong>{event['date']}</strong>: {event['title']}</li>"
        html += "</ul></body></html>"

        # Controleer of de map 'public' bestaat
        output_dir = "public"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # HTML opslaan
        output_file = os.path.join(output_dir, "agenda.html")
        with open(output_file, "w") as f:
            f.write(html)

        print(f"[INFO] Agenda opgeslagen in {output_file}")

# Asynchrone hoofdfunctie uitvoeren
asyncio.run(scrape())
