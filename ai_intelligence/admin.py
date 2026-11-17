from django.contrib import admin
from ai_intelligence.models import AIAnalysis, ClauseAnalysis, RiskFlag, AIModelMetrics


class ClauseAnalysisInline(admin.TabularInline):
    model = ClauseAnalysis
    extra = 0
    fields = ('clause_number', 'category', 'risk_score', 'confidence_score', 'sentiment')
    readonly_fields = fields
    can_delete = False


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ('mou', 'overall_risk_score', 'risk_level', 'compliance_status', 'model_used', 'analyzed_at')
    list_filter = ('risk_level', 'compliance_status', 'analyzed_at')
    search_fields = ('mou__title', 'executive_summary')
    inlines = [ClauseAnalysisInline]


@admin.register(RiskFlag)
class RiskFlagAdmin(admin.ModelAdmin):
    list_display = ('title', 'mou', 'risk_type', 'severity', 'is_resolved', 'created_at')
    list_filter = ('severity', 'risk_type', 'is_resolved')
    search_fields = ('title', 'description', 'mou__title')


@admin.register(AIModelMetrics)
class AIModelMetricsAdmin(admin.ModelAdmin):
    list_display = ('id', 'documents_analyzed', 'clauses_analyzed', 'average_processing_time', 'last_run')
