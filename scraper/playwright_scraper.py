from playwright.sync_api import sync_playwright

def run_search_scraper(query: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(f"https://builtwith.com/meta/{query}")
        blocks = page.locator('div.card-body').all()

        contact_block = verified_people_block = socials_block = listed_contacts = None
        people_verified = False
        for block in blocks:
            title = block.locator('h6').first.text_content().strip() or ''
            if title == 'Contact Information':
                contact_block = block.locator('dl.row').all()
            elif title == 'Verified People':
                verified_people_block = block
            elif title == 'Social Links':
                socials_block = block

        if contact_block:
            company_name = contact_block[0].locator('dd').inner_text().split('\n')[0].strip()
            company_address = contact_block[1].locator('address').inner_text().replace('\n', ' ').strip()
            company_phone_numbers = contact_block[1].locator('dd').all()[1].inner_text().strip()

        if verified_people_block:
            people_verified = True
            listed_contacts = blocks[0].locator('table').inner_html()

        if socials_block:
            socials = socials_block.locator('li a').all()
            social_urls = []
            for s in socials:
                url = s.get_attribute('href')
                social_urls.append(url.strip())


        browser.close()
        print(company_name)
        print(company_address)
        print(company_phone_numbers)
        print(listed_contacts)
        print(people_verified)
        print(social_urls)

run_search_scraper('shopware.com')