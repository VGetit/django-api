from playwright.sync_api import sync_playwright
from selectolax.parser import HTMLParser, Node

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

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
    with sync_playwright() as p:
        url = f"https://builtwith.com/meta/{target_url}"
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print(f"Navigating to {url}")
        page.goto(url)

        try:
            page.wait_for_selector('div.card', timeout=10000)
            page.wait_for_timeout(1000)  # Extra wait to ensure all content loads
        except:
            print("Timeout waiting for page to load.")

        html_content = page.content()

        browser.close()

        result = parse_html_content(html_content)
        return result


