import asyncio
from pyppeteer import launch
from datetime import datetime
import os
import locale  # <-- Nodig voor Nederlandse datums
import re      # <-- Nodig voor opschonen

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
        
        print("[DEBUG] Screenshot maken voor debug...")
        await page.screenshot({'path': 'screenshot_wedstrijdschema.png', 'fullPage': True})
        
        print("[INFO] Wachten op wedstrijdschema-selector...")
        await page.waitForSelector('.home-team', timeout=60000)
        
        print("[INFO] Wedstrijdschema laden...")
        # --- AANGEPASTE SCRAPER ---
        # Deze logica zoekt naar datums (gok: H3) en koppelt ze aan de 
        # wedstrijden (.single-item) die er direct onder vallen.
        matches_data = await page.evaluate('''() => {
            const matches = [];
            let currentDate = null;
            // Zoek de container met alle items. We nemen de parent van het eerste .single-item
            const listContainer = document.querySelector('.single-item')?.parentElement;
            
            if (!listContainer) return [];

            listContainer.childNodes.forEach(node => {
                if (node.nodeType !== 1) return; // Alleen element nodes

                // --- DIT IS EEN GOK ---
                // We gaan ervan uit dat de datum een H3-tag is.
                // Pas dit aan als de selector anders is (bv. '.date-header')
                if (node.tagName === 'H3') {
                    currentDate = node.innerText.trim();
                }
                // --- EINDE GOK ---

                if (node.classList.contains('single-item')) {
                    if (currentDate) { // Alleen toevoegen als we een datum hebben
                        matches.push({
                            date_str: currentDate,
                            home_team: node.querySelector('.home-team')?.innerText.trim(),
                            away_team: node.querySelector('.away-team')?.innerText.trim(),
                            time: node.querySelector('.main-time')?.innerText.trim(),
                            field: node.querySelector('.play-field')?.innerText.trim()
                        });
                    }
                }
            });
            return matches;
        }''')
        
        # --- PYTHON VERWERKING: FILTEREN EN GROEPEREN ---
        today = datetime.now()
        planned_matches = []

        for match in matches_data:
            try:
                # Combineer datum-string en tijd-string
                # (bv. "Zaterdag 26 oktober 2025" + "14:00")
                full_date_str = f"{match['date_str']} {match['time']}"
                
                # Verwijder ' Veld:' uit de veld-string
                match['field'] = match['field'].replace('Veld:', '').strip()

                # Parse de string naar een echt datetime object
                # %A = Volledige dagnaam (Zaterdag)
                # %d = dag (26)
                # %B = Volledige maandnaam (oktober)
                # %Y = Jaar (2025)
                # %H:%M = Tijd (14:00)
                parsed_date = datetime.strptime(full_date_str, "%A %d %B %Y %H:%M")

                # De belangrijkste check: is de wedstrijd in de toekomst?
                if parsed_date >= today:
                    match['datetime_obj'] = parsed_date
                    planned_matches.append(match)

            except Exception as e:
                print(f"[FOUT] Kon datum niet parsen: '{full_date_str}' - {e}")
        
        # Groepeer de gefilterde wedstrijden op dag
        grouped_matches = {}
        for match in planned_matches:
            date_header = match['datetime_obj'].strftime("%A %d %B %Y").capitalize()
            if date_header not in grouped_matches:
                grouped_matches[date_header] = []
            grouped_matches[date_header].append(match)


        # --- NIEUWE HTML GENERATIE ---
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
        <h2>Wedstrijdschema (Gepland)</h2>
        """

        if not grouped_matches:
            html += "<h3>Geen geplande wedstrijden gevonden.</h3>"

        for date_header, matches_in_day in grouped_matches.items():
            html += f"<h3>{date_header}</h3><ul>"
            for match in matches_in_day:
                html += f"<li><strong>{match['time']}</strong> {match['home_team']} vs {match['away_team']} <span>(Veld: {match['field']})</span></li>"
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
