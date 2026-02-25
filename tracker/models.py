from django.db import models
from django.contrib.auth.models import User


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('WFH', 'Work From Home'),
        ('Leave', 'Leave'),
        ('Half Day', 'Half Day'),
    ]

    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    extra_days = models.BooleanField(default=False, help_text="Check if worked on Sunday or weekend")

    def __str__(self):
        return f"{self.employee.username} - {self.date} - {self.status}"
    
    def hours_worked(self):
        """Calculate hours worked based on check-in and check-out times"""
        if self.check_in_time and self.check_out_time:
            from datetime import datetime, timedelta
            start = datetime.combine(self.date, self.check_in_time)
            end = datetime.combine(self.date, self.check_out_time)
            duration = end - start
            hours = duration.total_seconds() / 3600
            return round(hours, 2) if hours > 0 else 0
        return 0


class DailyReport(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    today_actions = models.TextField()
    outcomes = models.TextField()
    weekly_plan = models.TextField()
    dau_metric = models.TextField(blank=True, default="")
    grades_qa = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.employee.username} - {self.date}"
