# scraper/tasks.py
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from api.models import Company, PhoneNumber, Address, Contacts, TaskQueue
from api.builtwith_scraper import scrape_company_data
import phonenumbers

# Get rate limit from settings
SCRAPE_RATE_LIMIT = getattr(settings, 'SCRAPE_RATE_LIMIT', 5)

@shared_task
def queue_scrape_company(url):
    """
    Queues a company scrape task with rate limiting.
    If another task is running, adds to queue; otherwise starts immediately.
    """
    try:
        # Get or create task in queue
        task_queue, created = TaskQueue.objects.get_or_create(
            url=url,
            defaults={'status': 'pending'}
        )
        
        # Check if we should execute now or queue
        should_execute = should_execute_next_task()
        
        if should_execute:
            # Execute immediately
            task_queue.status = 'processing'
            task_queue.save()
            scrape_company_task.delay(url)
        else:
            # Queue for later (will be picked up by process_task_queue)
            task_queue.status = 'pending'
            task_queue.save()
            
    except Exception as e:
        print(f"Error queuing scrape task for {url}: {e}")

@shared_task
def process_task_queue():
    """
    Processes pending tasks from the queue based on rate limit.
    This should be called periodically (e.g., every 10 seconds via celery beat).
    """
    print("Processing task queue...")
    # Get pending tasks
    pending_tasks = TaskQueue.objects.filter(status='pending').order_by('created_at')
    
    for task in pending_tasks:
        if should_execute_next_task():
            task.status = 'processing'
            task.save()
            scrape_company_task.delay(task.url)
            break  # Only process one at a time
        else:
            break  # Wait for rate limit

def should_execute_next_task():
    """
    Check if we should execute the next task based on rate limiting.
    Returns True if enough time has passed since the last execution.
    """
    try:
        # Get the most recent completed task
        last_task = TaskQueue.objects.filter(
            status__in=['completed', 'processing']
        ).order_by('-last_executed_at').first()
        
        if not last_task or not last_task.last_executed_at:
            return True  # No previous task, execute immediately
        
        # Check if enough time has passed
        time_since_last = timezone.now() - last_task.last_executed_at
        return time_since_last.total_seconds() >= SCRAPE_RATE_LIMIT
        
    except Exception as e:
        print(f"Error checking rate limit: {e}")
        return True  # On error, allow execution

@shared_task
def scrape_company_task(url):
    """
    Scrapes company data and updates the company record.
    If no company name is found, deletes the company entry.
    """
    task_queue = None
    try:
        # Update task start time
        task_queue = TaskQueue.objects.get(url=url)
        task_queue.last_executed_at = timezone.now()
        task_queue.save()
        
        result = scrape_company_data(url)
        print(f"Scrape result for {url}: {result}")
        
        # Check if company name was found
        if not result.get('name') or result.get('name') == '':
            print(f"Company name is empty for URL {url}, deleting company entry.")
            Company.objects.filter(url=url).delete()
            
            # Mark task as completed
            task_queue.status = 'completed'
            task_queue.error_message = 'No company name found'
            task_queue.save()
            return
        
        # Create address
        addr = Address.objects.create(address=result.get('address', ''), verified=True)
        
        # Get or create company
        company, created = Company.objects.get_or_create(url=url, defaults={
            'name': result.get('name', ''),
            'address': addr,
            'is_processed': True,
            'social_urls': result.get('socials', ''),
        })

        # If company already existed, update it
        if not created:
            company.name = result.get('name', '')
            company.social_urls = result.get('socials', '')
            company.is_processed = True
            company.address = addr
            company.save()

        # Verify and create phone numbers
        phone_numbers_to_create = []
        for phone_data in result.get('phone_numbers', []):
            phone_number = phone_data.get('number', '')
            description = phone_data.get('description', '')

            is_verified = False
            try:
                parsed = phonenumbers.parse(phone_number)
                if phonenumbers.is_valid_number(parsed):
                    is_verified = True
            except phonenumbers.NumberParseException:
                is_verified = False
            
            phone_numbers_to_create.append(
                PhoneNumber(
                    company=company,
                    number=phone_number,
                    description=description,
                    verified=is_verified
                )
            )
        
        PhoneNumber.objects.bulk_create(phone_numbers_to_create)

        # Create contacts
        Contacts.objects.bulk_create([
            Contacts(company=company, **c)
            for c in result.get('listed_contacts', [])
        ])
        company.calculate_and_save_score()
        
        # Mark task as completed
        task_queue.status = 'completed'
        task_queue.error_message = None
        task_queue.save()
        
        # Process next task in queue
        process_task_queue.delay()
        
        print(f"Successfully processed company data for URL {url}")

    except Exception as e:
        print(f"Error processing company data for URL {url}: {e}")
        
        # Update task status
        if task_queue:
            task_queue.status = 'failed'
            task_queue.error_message = str(e)
            task_queue.retry_count += 1
            task_queue.save()
        
        # Delete the company entry if scraping failed
        try:
            Company.objects.filter(url=url).delete()
        except Exception:
            pass
        
        # Process next task in queue
        process_task_queue.delay()


