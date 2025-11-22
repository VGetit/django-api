from django.contrib import admin
from .models import Address, Company, Comment, PhoneNumber, Contacts, TaskQueue


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['id', 'address', 'verified']
    list_filter = ['verified']
    search_fields = ['address']
    plural_name = "Addresses"


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'slug', 'is_processed', 'score', 'created_at']
    list_filter = ['is_processed', 'created_at', 'last_updated']
    search_fields = ['name', 'url', 'slug']
    readonly_fields = ['slug', 'created_at', 'last_updated', 'score']
    plural_name = "Companies"
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'url', 'slug', 'about')
        }),
        ('Address & Location', {
            'fields': ('address',)
        }),
        ('Status & Scoring', {
            'fields': ('is_processed', 'score')
        }),
        ('Social Media', {
            'fields': ('social_urls',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_updated'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'rating', 'created_at']
    list_filter = ['rating', 'created_at', 'company']
    search_fields = ['user__username', 'company__name', 'text']
    readonly_fields = ['created_at']
    plural_name = "Comments"
    fieldsets = (
        ('Comment Information', {
            'fields': ('company', 'user', 'text')
        }),
        ('Rating', {
            'fields': ('rating',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ['company', 'number', 'verified', 'description']
    list_filter = ['verified', 'company']
    search_fields = ['number', 'company__name', 'description']
    plural_name = "Phone Numbers"
    fieldsets = (
        ('Phone Number Details', {
            'fields': ('company', 'number', 'description')
        }),
        ('Verification', {
            'fields': ('verified',)
        }),
    )


@admin.register(Contacts)
class ContactsAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'level', 'verified_profile']
    list_filter = ['verified_profile', 'level', 'company']
    search_fields = ['name', 'company__name', 'level']
    plural_name = "Contacts"
    fieldsets = (
        ('Contact Information', {
            'fields': ('company', 'name', 'level')
        }),
        ('Verification', {
            'fields': ('verified_profile',)
        }),
        ('Social Links', {
            'fields': ('google_link', 'linkedin_link')
        }),
    )


@admin.register(TaskQueue)
class TaskQueueAdmin(admin.ModelAdmin):
    list_display = ['url', 'status', 'retry_count', 'last_executed_at', 'created_at']
    list_filter = ['status', 'created_at', 'last_executed_at']
    search_fields = ['url', 'error_message']
    readonly_fields = ['created_at', 'updated_at', 'last_executed_at']
    plural_name = "Task Queue"
    fieldsets = (
        ('Task Information', {
            'fields': ('url', 'status')
        }),
        ('Execution Details', {
            'fields': ('last_executed_at', 'retry_count', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['retry_failed_tasks']
    
    def retry_failed_tasks(self, request, queryset):
        """Action to retry failed tasks"""
        failed_tasks = queryset.filter(status='failed')
        updated_count = failed_tasks.update(status='pending', retry_count=0)
        self.message_user(request, f'{updated_count} task(s) queued for retry.')
    
    retry_failed_tasks.short_description = "Retry selected failed tasks"
