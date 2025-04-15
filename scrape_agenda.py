import asyncio
from pyppeteer import launch
from datetime import datetime

async def scrape():
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()
    await page.goto('https://www.haackey.nl/agenda', waitUntil='networkidle2')
    await page.waitForSelector('.clsLISAAgDate', timeout=10000)

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

asyncio.get_event_loop().run_until_complete(scrape())
