import time
from selectolax.parser import HTMLParser, Node
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from playwright_scraper import parse_html_content
from api.captcha_solver import CaptchaAI
from pyvirtualdisplay import Display
import os
os.environ['PYVIRTUALDISPLAY_DISPLAYFD'] = '0'

def safe_get_text(node: Node, seperator=''):
    return node.text(strip=True, separator=seperator) if node else ''

def safe_get_html(node: Node):
    return node.html if node else ''

def parse_html_content(html_content: str):
    html = HTMLParser(html_content)

    company_name = company_address = ''
    people_verified = False
    social_urls = []
    table_data = []
    company_phone_numbers = []

    card_bodies = html.css('div.card')

    for block in card_bodies:
        title_node = block.css_first('.card-header')
        body_node = block.css_first('.card-body')
        if not title_node or not body_node:
            print("Missing title or body node in card block, skipping.")
            continue

        title = title_node.text(strip=True)

        if title == "Company Name":
            print("Extracting company name.")
            company_name = safe_get_text(body_node.css_first('p'))

        if title == "Location":
            company_address = safe_get_text(body_node.css_first('address'), seperator=' ')

        if title == "Telephones":
            for tel in body_node.css('div.row'):
                num = tel.css_first('div.col-lg-7')
                info = tel.css_first('div.col-lg-5')
                company_phone_numbers.append({'number': safe_get_text(num), 'description': safe_get_text(info)})

        elif title == 'Publicly Listed Contacts':
            table = body_node.css_first('table')
            if table:
                rows = table.css("table tbody tr")
                for row in rows:
                    cols = row.css("td")
                    if not cols or len(cols) < 3:
                        continue

                    people_verified = True
                    name_text = safe_get_text(cols[0])
                    verified = bool(cols[1].css_first("svg"))
                    level = safe_get_text(cols[2])
                    links_td = cols[3]
                    google_link = links_td.css_first("a[href*='google']")
                    linkedin_link = links_td.css_first("a[href*='linkedin']")

                    table_data.append({
                        "name": name_text,
                        "verified_profile": verified,
                        "level": level,
                        "google_link": google_link.attributes.get("href") if google_link else None,
                        "linkedin_link": linkedin_link.attributes.get("href") if linkedin_link else None
                    })

        elif title == 'Social Links':
            links = block.css('li a[href]')
            for link in links:
                href = link.attributes.get('href')
                if href:
                    social_urls.append(href.strip())

    return {
        'name': company_name,
        'address': company_address,
        'phone_numbers': company_phone_numbers,
        'verified_people_exist': people_verified,
        'socials': social_urls,
        'listed_contacts': table_data
    }

def scrape_company_data(target_url: str):
    ai_solver = CaptchaAI()

    captured_data = {
        "image_bytes": None,
        "target_label": None
    }

    with Display(visible=False, size=(1920, 1080)) as disp:
        print("display")
        with Stealth().use_sync(sync_playwright()) as p:
            print("browser")
            browser = p.chromium.launch_persistent_context(
                user_data_dir="./user_data",
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars"
                ],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = browser.new_page()

            def handle_response(response):
                if "human-test/prompt" in response.url and response.status == 200:
                    try:
                        json_data = response.json()
                        captured_data["target_label"] = json_data.get("label")
                        print(f"Hedef metin yakalandı: {captured_data['target_label']}")
                    except:
                        pass

            page.on("response", handle_response)

            print("Sayfaya gidiliyor...")
            page.goto(f"https://builtwith.com/meta/{target_url}")

            blob_selector = "img[src^='blob:']"
            try:
                page.wait_for_selector(blob_selector, state="visible", timeout=30000)
                page.wait_for_timeout(5000)

                if not captured_data["target_label"]:
                    return

                captured_data["image_bytes"] = page.locator(blob_selector).screenshot()

                target_idx = ai_solver.solve(
                    captured_data["image_bytes"],
                    captured_data["target_label"]
                )

                element_box = page.locator(blob_selector).bounding_box()

                if element_box:
                    w = element_box["width"]
                    h = element_box["height"]

                    tile_w = w / 4
                    tile_h = h / 2

                    row = target_idx // 4
                    col = target_idx % 4

                    click_x = element_box["x"] + (col * tile_w) + (tile_w / 2)
                    click_y = element_box["y"] + (row * tile_h) + (tile_h / 2)

                    page.mouse.move(click_x, click_y, steps=15)
                    time.sleep(0.2)
                    page.mouse.down()
                    time.sleep(0.1)
                    page.mouse.up()

                    time.sleep(5)
                else:
                    print("Hata: Görsel bounding box alınamadı.")

            except Exception as e:
                print(f"Bir hata oluştu veya captcha çıkmadı: {e}")

            html_content = page.content()

            browser.close()

            result = parse_html_content(html_content, 'test')
            return result


