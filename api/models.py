from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Avg
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from api.utils import custom_slugify
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
                else:
                    number.verified = False
            except phonenumbers.NumberParseException:
                number.verified = False
    
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