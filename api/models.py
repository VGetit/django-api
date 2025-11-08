from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
import phonenumbers

class Address(models.Model):
    address = models.TextField(blank=True, null=True)
    verified = models.BooleanField(default=False)

class Company(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=False)
    about = models.CharField(blank=True)
    address = models.OneToOneField(Address, on_delete=models.CASCADE, blank=True, null=True)
    slug = models.CharField(max_length=100, unique=True, blank=True)
    url = models.CharField(max_length=100, unique=True)
    is_processed = models.BooleanField(default=False)
    social_urls = models.TextField()
    score = models.SmallIntegerField(default=0)
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

    def save(self, *args, **kwargs):
        if not self.slug and self.url:
            #base_slug = slugify(self.url)
            #slug = base_slug
            #i = 1
            #while Company.objects.filter(slug=slug).exists():
            #    slug = f"{base_slug}-{i}"
            #    i += 1
            self.slug = self.url
        super().save(*args, **kwargs)
        self.verify_phone_numbers()

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