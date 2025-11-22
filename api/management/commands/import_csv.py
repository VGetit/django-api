import csv
import json
from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import Company, Address, PhoneNumber, Contacts
import phonenumbers

class Command(BaseCommand):
    help = 'Import companies from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')

    @transaction.atomic
    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                created_count = 0
                updated_count = 0
                error_count = 0
                
                for row_num, row in enumerate(reader, start=2):  # Start from 2 (header is 1)
                    try:
                        domain = row.get('domain', '').strip()
                        name = row.get('name', '').strip()
                        address_str = row.get('address', '').strip()
                        verified_people_exist = row.get('verified_people_exist', 'False').lower() == 'true'
                        phone_numbers_json = row.get('phone_numbers', '[]')
                        socials_json = row.get('socials', '[]')
                        contacts_json = row.get('listed_contacts', '[]')
                        
                        if not domain or not name:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: Missing domain or name, skipping')
                            )
                            error_count += 1
                            continue
                        
                        # Create or update Company
                        company_url = f'https://{domain}' if not domain.startswith('http') else domain
                        
                        company, created = Company.objects.update_or_create(
                            url=company_url,
                            defaults={
                                'name': name,
                                'is_processed': True,
                                'social_urls': socials_json,
                            }
                        )
                        
                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'Row {row_num}: Created company "{name}"')
                            )
                        else:
                            updated_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'Row {row_num}: Updated company "{name}"')
                            )
                        
                        # Handle Address
                        if address_str:
                            address, _ = Address.objects.update_or_create(
                                id=company.address_id if company.address_id else None,
                                defaults={
                                    'address': address_str,
                                    'verified': verified_people_exist,
                                }
                            )
                            company.address = address
                            company.save()
                        
                        # Handle Phone Numbers
                        PhoneNumber.objects.filter(company=company).delete()  # Clear existing
                        phone_numbers_to_create = []
                        
                        try:
                            phone_numbers_list = json.loads(phone_numbers_json)
                            for phone_data in phone_numbers_list:
                                phone_number = phone_data.get('number', '').strip()
                                description = phone_data.get('description', '').strip()
                                
                                if phone_number:
                                    is_verified = False
                                    try:
                                        parsed = phonenumbers.parse(phone_number, "US")
                                        if phonenumbers.is_valid_number(parsed):
                                            is_verified = True
                                    except phonenumbers.NumberParseException:
                                        is_verified = False
                                    
                                    phone_numbers_to_create.append(
                                        PhoneNumber(
                                            company=company,
                                            number=phone_number,
                                            description=description,
                                            verified=is_verified,
                                        )
                                    )
                        except json.JSONDecodeError:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: Invalid phone numbers JSON, skipping')
                            )
                        
                        if phone_numbers_to_create:
                            PhoneNumber.objects.bulk_create(phone_numbers_to_create)
                        
                        # Handle Contacts
                        Contacts.objects.filter(company=company).delete()  # Clear existing
                        contacts_to_create = []
                        
                        try:
                            contacts_list = json.loads(contacts_json)
                            for contact_data in contacts_list:
                                name_contact = contact_data.get('name', '').strip()
                                verified_profile = contact_data.get('verified_profile', False)
                                level = contact_data.get('level', 'Unknown').strip()
                                google_link = contact_data.get('google_link', '').strip()
                                linkedin_link = contact_data.get('linkedin_link', '').strip()
                                
                                if name_contact:
                                    contacts_to_create.append(
                                        Contacts(
                                            company=company,
                                            name=name_contact,
                                            verified_profile=verified_profile,
                                            level=level,
                                            google_link=google_link,
                                            linkedin_link=linkedin_link,
                                        )
                                    )
                        except json.JSONDecodeError:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: Invalid contacts JSON, skipping')
                            )
                        
                        if contacts_to_create:
                            Contacts.objects.bulk_create(contacts_to_create)
                        
                        # Recalculate score
                        company.calculate_and_save_score()
                        
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'Row {row_num}: Error - {str(e)}')
                        )
                
                # Summary
                self.stdout.write(self.style.SUCCESS('\n' + '='*50))
                self.stdout.write(self.style.SUCCESS(f'Import completed!'))
                self.stdout.write(self.style.SUCCESS(f'Created: {created_count}'))
                self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count}'))
                self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
                self.stdout.write(self.style.SUCCESS('='*50))
        
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'CSV file not found: {csv_file}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))