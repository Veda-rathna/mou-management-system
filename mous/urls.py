from django.urls import path
from mous import views

urlpatterns = [
    # Dashboard & MOU Lifecycle
    path('', views.mou_dashboard, name='mou_dashboard'),
    path('mous/create/', views.mou_create, name='mou_create'),
    path('mous/<int:pk>/', views.mou_detail, name='mou_detail'),
    path('mous/<int:pk>/edit/', views.mou_edit, name='mou_edit'),
    path('mous/<int:pk>/share/', views.generate_share_link, name='generate_share_link'),
    path('mous/<int:pk>/college-sign/', views.college_approve_and_sign, name='college_approve_and_sign'),
    path('mous/<int:pk>/request-changes/', views.request_partner_changes, name='request_partner_changes'),
    path('mous/<int:pk>/reanalyze/', views.reanalyze_mou, name='reanalyze_mou'),
    path('mous/<int:pk>/executive-summary/', views.executive_summary_view, name='executive_summary'),
    path('mous/<int:pk>/audit-log/', views.audit_log_view, name='audit_log'),

    # Activity Log Trail
    path('activity/', views.global_activity_log, name='global_activity_log'),

    # Risk Flag Resolution
    path('flags/<int:flag_id>/resolve/', views.resolve_risk_flag, name='resolve_risk_flag'),

    # External Partner Public Collaboration Portal
    path('partner/<uuid:token>/', views.partner_portal, name='partner_portal'),
    path('partner/<uuid:token>/success/', views.partner_success, name='partner_success'),
]
