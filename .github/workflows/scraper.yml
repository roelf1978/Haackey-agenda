import asyncio
from pyppeteer import launch
from datetime import datetime

async def scrape():
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()

    print("[INFO] Pagina openen...")
    await page.goto('https://www.haackey.nl/agenda', waitUntil='networkidle2')

    try:
        print("[INFO] Wachten op agenda-selector...")
        await page.waitForSelector('.clsLISAAgDate', timeout=30000)  # 30 seconden
    except Exception as e:
        print("[FOUT] Agenda-element niet gevonden:", e)
        await browser.close()
        return

    print("[INFO] Agenda laden...")
    events = await page.evaluate('''() => {
        return Array.from(document.querySelectorAll('.clsResultDiv')).map(el => {
            return {
                date: el.querySelector('.clsLISAAgDate')?.innerText.trim(),
                title: el.querySelector('.clsLISAAgTitle')?.innerText.trim()
            };
        });
    }''')

    html = "<html><head><meta charset='UTF-8'><style>body{font-family:sans-serif;}</style></head><body>"
    html += f"<h2>Agenda - HHC Haackey ({datetime.now().strftime('%d-%m-%Y')})</h2><ul>"
    for event in events:
        html += f"<li><strong>{event['date']}</strong>: {event['title']}</li>"
    html += "</ul></body></html>"

    with open("public/agenda.html", "w") as f:
        f.write(html)

    print("[INFO] Agenda opgeslagen.")
    await browser.close()

asyncio.get_event_loop().run_until_complete(scrape())
