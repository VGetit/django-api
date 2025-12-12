from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Avg
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from api.utils import custom_slugify, get_phone_number_type_description, get_whois_details
import phonenumbers

class Address(models.Model):
    address = models.TextField(blank=True, null=True)
    verified = models.BooleanField(default=False)

class Company(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=False)
    about = models.CharField(blank=True)
    address = models.OneToOneField(Address, on_delete=models.CASCADE, blank=True, null=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    url = models.CharField(max_length=100, unique=True)
    parent_company = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='branches')
    registration_date = models.DateField(null=True, blank=True)
    legal_status = models.CharField(max_length=255, blank=True, null=True)
    origin_country = models.CharField(max_length=100, blank=True, null=True)
    is_processed = models.BooleanField(default=False)
    social_urls = models.TextField(blank=True, null=True)
    score = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def verify_phone_numbers(self):
        numbers = self.phone_numbers.all()
        for number in numbers:
            try:
                parsed = phonenumbers.parse(number.number)
                if phonenumbers.is_valid_number(parsed):
                    number.verified = True
                    num_type = phonenumbers.number_type(parsed)
                    number.description = get_phone_number_type_description(num_type)
                else:
                    number.verified = False
            except phonenumbers.NumberParseException:
                number.verified = False
            number.save()
    
    def calculate_and_save_score(self):
        verification_score = 0
        
        if self.address and self.address.verified:
            verification_score += 1.0
            
        if self.phone_numbers.filter(verified=True).exists():
            verification_score += 1.0

        if self.contacts.filter(verified_profile=True).exists():
            verification_score += 1.0
            
    
        avg_rating = self.comments.aggregate(Avg('rating'))['rating__avg'] or 0
        final_score = verification_score + (float(avg_rating) * 0.4)
        self.score = round(min(final_score, 5.0), 1)
        self.save(update_fields=['score'])

    def save(self, *args, **kwargs):
        if not self.slug and self.url:
            self.slug = custom_slugify(self.url)
            original_slug = self.slug
            i = 1
            while Company.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{i}"
                i += 1
        
        # Auto-populate WHOIS data if fields are missing
        if self.url and (not self.registration_date or not self.legal_status or not self.origin_country):
            try:
                whois_data = get_whois_details(self.url)
                if whois_data:
                    if not self.registration_date and whois_data.get('registration_date'):
                        self.registration_date = whois_data.get('registration_date')
                    if not self.legal_status and whois_data.get('legal_status'):
                        self.legal_status = whois_data.get('legal_status')
                    if not self.origin_country and whois_data.get('origin_country'):
                        self.origin_country = whois_data.get('origin_country')
            except Exception as e:
                # Log error or silently fail to avoid blocking save
                print(f"Error fetching WHOIS data for {self.url}: {e}")

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Comment(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(max_length=1000)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('company', 'user')

    def __str__(self):
        return f'{self.user.username} - {self.company.name} ({self.rating} stars)'

class PhoneNumber(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='phone_numbers')
    number = models.CharField(max_length=50)
    verified = models.BooleanField(default=False)
    description = models.CharField(max_length=100, blank=True, null=True)

class Contacts(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=255)
    verified_profile = models.BooleanField(default=False)
    level = models.CharField(max_length=100)
    google_link = models.CharField(max_length=255)
    linkedin_link = models.CharField(max_length=255)

class TaskQueue(models.Model):
    """
    Model to track scraping tasks in a queue.
    Implements rate limiting between task executions.
    """
    url = models.CharField(max_length=255, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    last_executed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.url} - {self.status}"


@receiver(post_save, sender=Address)
def update_score_on_address_change(sender, instance, **kwargs):
    if hasattr(instance, 'company'):
        instance.company.calculate_and_save_score()

@receiver(post_save, sender=PhoneNumber)
@receiver(post_delete, sender=PhoneNumber)
def update_score_on_phone_change(sender, instance, **kwargs):
    if instance.company:
        instance.company.calculate_and_save_score()

@receiver(post_save, sender=Comment)
@receiver(post_delete, sender=Comment)
def update_score_on_comment_change(sender, instance, **kwargs):
    if instance.company:
        instance.company.calculate_and_save_score()


@receiver(post_save, sender=Address)
def trigger_address_verification(sender, instance, created, **kwargs):
    update_fields = kwargs.get('update_fields')
    
    # If update_fields is present and ONLY contains 'verified', do not re-verify
    if update_fields and 'verified' in update_fields and len(update_fields) == 1:
        return

    # To avoid circular import
    from api.tasks import verify_address_task
    
    verify_address_task.delay(instance.id)


@receiver(post_save, sender=PhoneNumber)
def verify_phone_number_on_change(sender, instance, created, **kwargs):
    update_fields = kwargs.get('update_fields')
    
    # If this save is just updating the 'verified' status (and potentially description), stop to prevent recursion
    if update_fields and 'verified' in update_fields:
        return

    # Perform synchronous verification
    try:
        parsed = phonenumbers.parse(instance.number)
        is_valid = False
        new_description = instance.description
        
        if phonenumbers.is_valid_number(parsed):
            is_valid = True
            num_type = phonenumbers.number_type(parsed)
            new_description = get_phone_number_type_description(num_type)
        
        # Only save if status changes or description changes
        should_save = False
        fields_to_update = []

        if instance.verified != is_valid:
            instance.verified = is_valid
            should_save = True
            fields_to_update.append('verified')
        
        if is_valid and instance.description != new_description:
            instance.description = new_description
            should_save = True
            fields_to_update.append('description')

        if should_save:
            # Ensure 'verified' is always in update_fields so recursion check works
            if 'verified' not in fields_to_update:
                fields_to_update.append('verified')
            instance.save(update_fields=fields_to_update)
            
    except phonenumbers.NumberParseException:
        if instance.verified:
            instance.verified = False
            instance.save(update_fields=['verified'])