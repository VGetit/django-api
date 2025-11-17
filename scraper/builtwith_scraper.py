import requests
from selectolax.parser import HTMLParser, Node

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

def safe_get_text(node: Node, seperator=''):
    return node.text(strip=True, separator=seperator) if node else ''

def safe_get_html(node: Node):
    return node.html if node else ''

def run_search_scraper_light(query: str):
    url = f"https://builtwith.com/meta/{query}"
    response = requests.get(url, headers=HEADERS)
    response.encoding = 'utf-8'
    html = HTMLParser(response.text)

    company_name = company_address = ''
    people_verified = False
    social_urls = []
    table_data = []
    company_phone_numbers = []

    card_bodies = html.css('div.card')
    for block in card_bodies:
        title_node = block.css_first('.card-header')
        body_node = block.css_first('.card-body')
        if not title_node:
            continue

        title = title_node.text(strip=True)

        if title == "Company Name":
            company_name = safe_get_text(body_node.css_first('p'))

        if title == "Location":
            company_address = safe_get_text(body_node.css_first('address'), seperator=' ')

        if title == "Telephones":
            for tel in body_node.css('div.row'):
                num = tel.css_first('div.col-lg-7')
                info = tel.css_first('div.col-lg-5')
                company_phone_numbers.append({'phone': safe_get_text(num), 'info': safe_get_text(info)})

        elif title == 'Publicly Listed Contacts':
            people_verified = True
            table = body_node.css_first('table')
            if table:
                rows = table.css("table tbody tr")

                for row in rows:
                    cols = row.css("td")
                    if not cols or len(cols) < 3:
                        continue

                    name_td = cols[0]
                    name_text = name_td.text(strip=True)

                    verified_icon = cols[1].css_first("svg")
                    verified = bool(verified_icon)

                    level = cols[2].text(strip=True)

                    links_td = cols[3]
                    google_link = links_td.css_first("a[href*='google']")
                    linkedin_link = links_td.css_first("a[href*='linkedin']")

                    entry = {
                        "name": name_text,
                        "verified_profile": verified,
                        "level": level,
                        "google_link": google_link.attributes.get("href") if google_link else None,
                        "linkedin_link": linkedin_link.attributes.get("href") if linkedin_link else None
                    }

                    table_data.append(entry)

        elif title == 'Social Links':
            links = block.css('li a[href]')
            for link in links:
                href = link.attributes.get('href')
                if href:
                    social_urls.append(href.strip())

    results = {
        'name': company_name,
        'address': company_address,
        'phone_numbers': company_phone_numbers,
        'verified_people_exist': people_verified,
        'socials': social_urls,
        'listed_contacts': table_data
    }
    return results


