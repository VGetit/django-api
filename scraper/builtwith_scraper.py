import requests
from selectolax.parser import HTMLParser

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

def run_search_scraper_light(query: str):
    url = f"https://builtwith.com/meta/{query}"
    response = requests.get(url, headers=HEADERS)
    response.encoding = 'utf-8'
    html = HTMLParser(response.text)

    company_name = company_address = company_phone_numbers = listed_contacts = ''
    people_verified = False
    social_urls = []
    table_data = []

    card_bodies = html.css('div.card-body')
    for block in card_bodies:
        title_node = block.css_first('h6')
        if not title_node:
            continue

        title = title_node.text(strip=True)

        # Contact Information
        if title == 'Contact Information':
            dls = block.css('dl.row')
            if len(dls) >= 2:
                try:
                    company_name = dls[0].css_first('dd').html.split('<br>')[0]
                    company_name = HTMLParser(company_name).text(strip=True)
                    company_address = dls[1].css_first('address').text(separator=' ', strip=True)
                    phone_dds = dls[1].css('dd')
                    if len(phone_dds) > 1:
                        company_phone_numbers = [HTMLParser(num).text().replace('\n', '').replace('-', '') for num in phone_dds[1].html.split('<br>')]
                except Exception as e:
                    print("Error parsing contact block:", e)

        # Verified People
        elif title == 'Verified People':
            people_verified = True
            table = card_bodies[0].css_first('table')
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

        # Social Links
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


