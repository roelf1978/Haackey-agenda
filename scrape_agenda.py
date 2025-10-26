import asyncio
from pyppeteer import launch
from datetime import datetime
import os
import re
import locale # <-- NIEUW

async def scrape():
    # Probeer Nederlandse locale in te stellen voor maandnamen
    try:
        locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Dutch_Netherlands.1252')
        except locale.Error:
            print("[WAARSCHUWING] Kon Nederlandse locale niet instellen. Maandnamen zijn mogelijk in het Engels.")

    # Browser lanceren met extra argumenten
    print("[INFO] Browser starten...")
    browser = await launch(
        headless=True,
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
                    month = parsed_date.strftime("%B %Y").capitalize() # Maakt 'oktober' -> 'Oktober'
                    
                    # Sla een duidelijk leesbare datum en tijd op voor de weergave (bv. "Zo 26, 14:00")
                    event['display_date'] = parsed_date.strftime("%a %d, %H:%M")

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
                    margin: 0;
                    padding: 0;
                }
                .slide {
                    width: 90%; /* Iets smaller voor ademruimte */
                    margin: 0 auto; /* Centreren */
                }
                h2 {
                    font-size: clamp(24px, 5vw, 60px);
                }
                h3 {
                    /* Stijl voor de Maand (bv. "Oktober 2025") */
                    font-size: clamp(22px, 4vw, 52px);
                    color: #f0e68c; /* Lichtgeel */
                    border-bottom: 2px solid #f0e68c;
                    padding-bottom: 10px;
                    margin-top: 30px;
                }
                ul {
                    list-style-type: none;
                    padding: 0;
                    margin: 0 auto; /* Centreer de lijst */
                }
                li {
                    font-size: clamp(18px, 2.5vw, 36px);
                    margin: 15px 0;
                    padding: 15px;
                    display: flex; /* Maak flexbox voor uitlijning */
                    align-items: center;
                    text-align: left; /* Lijn tekst links uit */
                    background: rgba(255, 255, 255, 0.05); /* Lichte achtergrond per item */
                    border-radius: 8px;
                }
                li strong {
                    /* Stijl voor de datum/tijd (bv. "Zo 26, 14:00") */
                    font-size: clamp(20px, 2.8vw, 40px);
                    color: #f0e68c; /* Lichtgeel - goed leesbaar */
                    min-width: 190px; /* Zorgt dat alle datums gelijk uitlijnen */
                    margin-right: 25px;
                    flex-shrink: 0; /* Voorkom dat de datum krimpt */
                    font-weight: 700;
                }
            </style>
        </head>
        <body>
        <div class="slide">
        <h2>Agenda</h2>
        """

        for month, events_in_month in grouped_events.items():
            html += f"<h3>{month}</h3><ul>"
            for event in events_in_month:
                # Dit is de gecorrigeerde, duidelijkere HTML-regel
                html += f"<li><strong>{event['display_date']}</strong> {event['title']}</li>"
            html += "</ul>"

        html += "</div></body></html>"
        
        # Controleer of de map 'public' bestaat
        output_dir = "public"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # HTML opslaan
        output_file = os.path.join(output_dir, "agenda.html")
        with open(output_file, "w", encoding='utf-8') as f: # Encoding toegevoegd
            f.write(html)
        print(f"[INFO] Agenda opgeslagen in {output_file}")
    except Exception as e:
        print(f"[FOUT] Er is een fout opgetreden: {e}")
    finally:
        # Browser sluiten
        await browser.close()

# Asynchrone hoofdfunctie uitvoeren
asyncio.run(scrape())
