import asyncio
from pyppeteer import launch
from datetime import datetime, timedelta # <-- Timedelta is nieuw
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

        # --- NIEUWE LOGICA: BEREKEN DEZE WEEK (MA-ZO) ---
        today_dt = datetime.now().date()
        start_of_week = today_dt - timedelta(days=today_dt.weekday()) # Weekday() geeft 0 voor Maandag, 6 voor Zondag
        end_of_week = start_of_week + timedelta(days=6)
        print(f"[INFO] Zoeken naar wedstrijden in de huidige week (Maandag {start_of_week} t/m Zondag {end_of_week})...")
        
        # Stap 2: Filter datums die binnen DEZE week vallen
        this_week_options = []
        for option in date_options:
            try:
                option_date = datetime.strptime(option['value'], "%Y-%m-%dT%H:%M:%SZ").date()
                
                # Check of de datum in de dropdown binnen de berekende week valt
                if start_of_week <= option_date <= end_of_week:
                    option['parsed_date'] = option_date # Sla de geparste datum op
                    this_week_options.append(option)
            except Exception as e:
                print(f"[WAARSCHUWING] Kon datum niet parsen: {option['value']} - {e}")

        print(f"[INFO] {len(this_week_options)} speeldagen gevonden in de dropdown voor deze week.")

        all_matches_this_week = []
        
        # Stap 3: Loop door elke datum IN DEZE WEEK en scrape de wedstrijden
        for option in this_week_options:
            print(f"[INFO] Bezig met scrapen van: {option['text']}...")
            
            await page.select('.date-selector', option['value'])
            
            try:
                await page.waitForSelector('.upcoming-matches-loader', {'visible': True, 'timeout': 5000})
            except Exception:
                print("[WAARSCHUWING] Loader verscheen niet, ga toch door...")
            
            try:
                await page.waitForSelector('.upcoming-matches-loader', {'hidden': True, 'timeout': 10000})
            except Exception:
                print(f"[FOUT] Loader bleef zichtbaar. Scrapen mislukt voor {option['text']}.")
                continue
                
            matches_on_this_day = await page.evaluate('''() => {
                const matches = [];
                document.querySelectorAll('.matches-container .single-item').forEach(el => {
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
            
            day_header = option['parsed_date'].strftime("%A %d %B %Y").capitalize()
            
            for match in matches_on_this_day:
                match['day_header'] = day_header
                # --- BELANGRIJK: We filteren GEEN wedstrijden op tijd meer ---
                all_matches_this_week.append(match)


        # Stap 4: Groepeer alle gevonden wedstrijden
        grouped_matches = {}
        for match in all_matches_this_week:
            date_header = match['day_header']
            if date_header not in grouped_matches:
                grouped_matches[date_header] = []
            grouped_matches[date_header].append(match)


        # --- HTML GENERATIE (zelfde als agenda) ---
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
                    color: #f0e68c;
                    min-width: 130px; /* Kleinere breedte dan agenda */
                    margin-right: 25px;
                    flex-shrink: 0;
                    font-weight: 700;
                }
                li span {
                    /* Stijl voor het veld (bv. "(Veld: 3)") */
                    margin-left: auto; /* Duwt het veld naar rechts */
                    padding-left: 20px;
                    font-size: clamp(16px, 2.2vw, 32px);
                    color: #ccc;
                    font-style: italic;
                }
            </style>
        </head>
        <body>
        <div class="slide">
        <h2>Wedstrijdschema (Deze Week)</h2> """

        if not grouped_matches:
            html += f"<h3>Geen wedstrijden gevonden voor deze week ({start_of_week.strftime('%d-%m')} t/m {end_of_week.strftime('%d-%m')}).</h3>"

        for date_header, matches_in_day in grouped_matches.items():
            html += f"<h3>{date_header}</h3><ul>"
            for match in matches_in_day:
                field_text = f"(Veld: {match['field']})" if match['field'] else ""
                html += f"<li><strong>{match['time']}</strong> {match['home_team']} vs {match['away_team']} <span>{field_text}</span></li>"
            html += "</ul>"

        html += "</div></body></html>"
        
        output_dir = "public"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_file = os.path.join(output_dir, "wedstrijdschema.html")
        with open(output_file, "w", encoding='utf-8') as f:
            f.write(html)
        print(f"[INFO] Wedstrijdschema opgeslagen in {output_file}")
        
    except Exception as e:
        print(f"[FOUT] Er is een algemene fout opgetreden: {e}")
    finally:
        await browser.close()
        print("[INFO] Browser gesloten.")

# Asynchrone hoofdfunctie uitvoeren
asyncio.run(scrape_wedstrijdschema())
