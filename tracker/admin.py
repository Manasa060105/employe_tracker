from django.contrib import admin
from .models import Attendance
from .models import DailyReport


class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'status', 'check_in_time', 'check_out_time', 'extra_days')
    list_filter = ('status', 'date', 'extra_days')
    search_fields = ('employee__username',)
    
    fieldsets = (
        ('Employee Information', {
            'fields': ('employee', 'date')
        }),
        ('Attendance Details', {
            'fields': ('status', 'check_in_time', 'check_out_time')
        }),
        ('Extra Information', {
            'fields': ('extra_days',)
        }),
    )
    
    def has_add_permission(self, request):
        return True
    
    def has_change_permission(self, request, obj=None):
        return True
    
    def has_delete_permission(self, request, obj=None):
        return True


class DailyReportAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date')
    list_filter = ('date',)
    search_fields = ('employee__username',)


admin.site.register(Attendance, AttendanceAdmin)
admin.site.register(DailyReport, DailyReportAdmin)
