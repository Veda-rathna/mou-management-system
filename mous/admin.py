from django.contrib import admin
from mous.models import MOU, ShareLink, PartnerSubmission, ActivityLog


@admin.register(MOU)
class MOUAdmin(admin.ModelAdmin):
    list_display = ('title', 'partner_organization', 'partner_name', 'status', 'expiry_date', 'created_at')
    list_filter = ('status', 'department', 'created_at', 'expiry_date')
    search_fields = ('title', 'partner_name', 'partner_organization', 'partner_email')
    date_hierarchy = 'created_at'


@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ('mou', 'token', 'expires_at', 'access_count', 'max_access_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'expires_at')
    search_fields = ('mou__title', 'token')


@admin.register(PartnerSubmission)
class PartnerSubmissionAdmin(admin.ModelAdmin):
    list_display = ('partner_name', 'partner_organization', 'mou', 'submitted_at', 'ip_address')
    search_fields = ('partner_name', 'partner_organization', 'partner_email', 'mou__title')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'mou', 'action', 'actor_name', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('mou__title', 'actor_name', 'description')
