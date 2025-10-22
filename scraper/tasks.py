# scraper/tasks.py
from celery import shared_task
from api.models import Company, PhoneNumber, Address, Contacts
from scraper.builtwith_scraper import run_search_scraper_light

@shared_task
def scrape_company_task(url):
    result = run_search_scraper_light(url)
    try:
        addr = Address.objects.create(address=result.get('address', ''), verified=False)
        print(addr)
        company, created = Company.objects.get_or_create(url=url, defaults={
            'name': result.get('name', ''),
            'address': addr,
            'is_processed': True,
            'social_urls': result.get('socials', ''),
        })

        if not created:
            company.name = result.get('name', '')
            company.social_urls = result.get('socials', '')
            company.is_processed = True
            company.address = addr
            company.save()

        PhoneNumber.objects.bulk_create([
            PhoneNumber(company=company, number=num)
            for num in result.get('phone_numbers', [])
        ])

        Contacts.objects.bulk_create([
            Contacts(company=company, **c)
            for c in result.get('listed_contacts', [])
        ])

    except Exception as e:
        print(f"Hata oluştu: {e}")
