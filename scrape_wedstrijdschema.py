import asyncio
from pyppeteer import launch
from datetime import datetime
import os
import locale
import re

async def scrape_wedstrijdschema():
    # Probeer Nederlandse locale in te stellen voor maand/dag namen
    try:
        locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Dutch_Netherlands.1252')
        except locale.Error:
            print("[WAARSCHUWING] Kon Nederlandse locale niet instellen. Datum-parsing mislukt mogelijk.")

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
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
        
        print("[INFO] Pagina openen...")
        await page.goto('https://www.haackey.nl/wedstrijdschema', waitUntil='networkidle2')
        
        await asyncio.sleep(5)
        
        try:
            await page.waitForSelector('.cookie-button', timeout=10000)
            await page.click('.cookie-button')
            print("[INFO] Cookie banner weggeklikt")
        except Exception as e:
            print("[INFO] Geen cookie banner gevonden of andere fout:", e)
        
        print("[INFO] Wachten op date-selector...")
        await page.waitForSelector('.date-selector')
        
        # Stap 1: Haal alle beschikbare datums uit de dropdown
        date_options = await page.evaluate('''() => {
            const options = [];
            document.querySelectorAll('.date-selector optgroup').forEach(optgroup => {
                const month = optgroup.label;
                optgroup.querySelectorAll('option').forEach(option => {
                    options.push({
                        value: option.value, // "2025-10-26T00:00:00Z"
                        collection: option.dataset.collection, // "matches_oct_2025"
                        text: option.innerText // "Zondag 26-10-2025"
                    });
                });
            });
            return options;
        }''')

        # Stap 2: Filter deze datums om alleen vandaag en de toekomst te krijgen
        today_dt = datetime.now().date()
        future_options = []
        for option in date_options:
            try:
                option_date = datetime.strptime(option['value'], "%Y-%m-%dT%H:%M:%SZ").date()
                if option_date >= today_dt:
                    option['parsed_date'] = option_date # Sla de geparste datum op
                    future_options.append(option)
            except Exception as e:
                print(f"[WAARSCHUWING] Kon datum niet parsen: {option['value']} - {e}")

        print(f"[INFO] {len(future_options)} toekomstige speeldagen gevonden. Bezig met scrapen...")

        all_planned_matches = []
        
        # Stap 3: Loop door elke toekomstige datum en scrape de wedstrijden
        for option in future_options:
            print(f"[INFO] Bezig met scrapen van: {option['text']}...")
            
            # Selecteer de datum in de dropdown
            await page.select('.date-selector', option['value'])
            
            # Wacht tot de loader verschijnt (betekent dat de JS de wijziging heeft opgepakt)
            try:
                await page.waitForSelector('.upcoming-matches-loader', {'visible': True, 'timeout': 5000})
            except Exception:
                print("[WAARSCHUWING] Loader verscheen niet, ga toch door...")
            
            # Wacht tot de loader verdwijnt (betekent dat de nieuwe wedstrijden zijn geladen)
            try:
                await page.waitForSelector('.upcoming-matches-loader', {'hidden': True, 'timeout': 10000})
            except Exception:
                print(f"[FOUT] Loader bleef zichtbaar. Scrapen mislukt voor {option['text']}.")
                continue
                
            # Scrape de wedstrijden die *nu* zichtbaar zijn
            matches_on_this_day = await page.evaluate('''() => {
                const matches = [];
                document.querySelectorAll('.matches-container .single-item').forEach(el => {
                    // Sla de template over (die is verborgen)
                    if (el.style.display === 'none') return; 
                    
                    matches.push({
                        home_team: el.querySelector('.home-team')?.innerText.trim(),
                        away_team: el.querySelector('.away-team')?.innerText.trim(),
                        time: el.querySelector('.main-time')?.innerText.trim(),
                        field: el.querySelector('.play-field')?.innerText.trim().replace('Veld:', '').trim()
                    });
                });
                return matches;
            }''')
            
            # Voeg de datum-info toe aan elke wedstrijd en sla op
            day_header = option['parsed_date'].strftime("%A %d %B %Y").capitalize()
            
            for match in matches_on_this_day:
                match['day_header'] = day_header
                
                # Filter wedstrijden die vandaag al geweest zijn (op tijd)
                try:
                    match_time = datetime.strptime(match['time'], "%H:%M").time()
                    if option['parsed_date'] == today_dt and match_time < datetime.now().time():
                        continue # Deze is vandaag, maar al geweest
                    all_planned_matches.append(match)
                except Exception:
                     all_planned_matches.append(match) # Tijd onbekend? Altijd toevoegen.


        # Stap 4: Groepeer alle gevonden wedstrijden
        grouped_matches = {}
        for match in all_planned_matches:
            date_header = match['day_header']
            if date_header not in grouped_matches:
                grouped_matches[date_header] = []
            grouped_matches[date_header].append(match)


        # --- NIEUWE HTML GENERATIE (zelfde als agenda) ---
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
                    width: 90%;
                    margin: 0 auto;
                }
                h2 {
                    font-size: clamp(24px, 5vw, 60px);
                }
                h3 {
                    /* Stijl voor de Dag (bv. "Zaterdag 26 Oktober") */
                    font-size: clamp(22px, 4vw, 52px);
                    color: #f0e68c; /* Lichtgeel */
                    border-bottom: 2px solid #f0e68c;
                    padding-bottom: 10px;
                    margin-top: 30px;
                }
                ul {
                    list-style-type: none;
                    padding: 0;
                    margin: 0 auto;
                }
                li {
                    font-size: clamp(18px, 2.5vw, 36px);
                    margin: 15px 0;
                    padding: 15px;
                    display: flex;
                    align-items: center;
                    text-align: left;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                }
                li strong {
                    /* Stijl voor de tijd (bv. "14:00") */
                    font-size: clamp(20px, 2.8vw, 40px);
                    color: #f0e6
