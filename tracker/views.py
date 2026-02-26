from django.shortcuts import render, redirect, get_object_or_404
import json
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User

from .models import Attendance, DailyReport, GeneratedCredential, EmployeeProfile


# =============================
# ✅ HOME REDIRECT
# =============================
@login_required
def home(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")
    else:
        return redirect("mark_attendance")


# =============================
# ✅ MARK ATTENDANCE + DAILY REPORT
# =============================
@login_required
def mark_attendance(request):
    # Redirect staff members to admin dashboard
    if request.user.is_staff:
        return redirect("admin_dashboard")

    today = timezone.now().date()

    # Get or create today's daily report
    report, created = DailyReport.objects.get_or_create(
        employee=request.user,
        date=today,
        defaults={
            "additional_actions": "",
            "outcomes": "",
            "weekly_plan": "",
            "team_metrics": {},
        }
    )

    # Check if attendance already marked
    already_marked = Attendance.objects.filter(
        employee=request.user,
        date=today
    ).exists()

    if request.method == "POST":

        # ✅ DAILY REPORT SAVE
        if "save_report" in request.POST:
            report.additional_actions = request.POST.get("additional_actions", "")
            report.outcomes = request.POST.get("outcomes", "")
            report.weekly_plan = request.POST.get("weekly_plan", "")
            report.dau_metric = request.POST.get("dau_metric", "")
            report.grades_qa = request.POST.get("grades_qa", "")

            user_team = getattr(request.user.profile, 'team', None) if hasattr(request.user, 'profile') else None
            metrics = {}
            if user_team == 'Growth and Marketing':
                metrics['new_leads'] = request.POST.get('new_leads', 0)
                metrics['pu_conversions'] = request.POST.get('pu_conversions', 0)
                metrics['lgs_conversions'] = request.POST.get('lgs_conversions', 0)
                metrics['summer_conversions'] = request.POST.get('summer_conversions', 0)
                metrics['cet_conversions'] = request.POST.get('cet_conversions', 0)
            elif user_team == 'Tech and Development':
                metrics['lessons_completed'] = request.POST.get('lessons_completed', 0)
                metrics['skills_added'] = request.POST.get('skills_added', 0)
                metrics['students_mentored'] = request.POST.get('students_mentored', 0)
                metrics['hours_mentored'] = request.POST.get('hours_mentored', 0)

            report.team_metrics = metrics
            report.save()

            messages.success(request, "Daily report saved.")
            return redirect("mark_attendance")

        # ✅ UPDATE TIMES OR MARK ATTENDANCE
        if "status" in request.POST:
            selected_status = request.POST.get("status")

            if selected_status not in ["Present", "Absent", "Half Day", "WFH", "Leave"]:
                messages.error(request, "Invalid attendance status.")
                return redirect("mark_attendance")

            check_in_time = request.POST.get("check_in_time")
            check_out_time = request.POST.get("check_out_time")
            extra_days = request.POST.get("extra_days") == "on"

            # If already marked, update the record instead of creating new one
            if already_marked:
                today_attendance = Attendance.objects.get(
                    employee=request.user,
                    date=today
                )
                today_attendance.status = selected_status
                today_attendance.check_in_time = check_in_time if check_in_time else None
                today_attendance.check_out_time = check_out_time if check_out_time else None
                today_attendance.extra_days = extra_days
                today_attendance.save()
                messages.success(request, "Attendance updated successfully!")
            else:
                Attendance.objects.create(
                    employee=request.user,
                    date=today,
                    status=selected_status,
                    check_in_time=check_in_time if check_in_time else None,
                    check_out_time=check_out_time if check_out_time else None,
                    extra_days=extra_days
                )
                messages.success(
                    request,
                    f"Attendance marked as {selected_status}!"
                )

        return redirect("mark_attendance")

    # ✅ GET REQUEST
    records = Attendance.objects.filter(
        employee=request.user
    ).order_by("-date")

    # Get today's attendance if already marked
    today_attendance = Attendance.objects.filter(
        employee=request.user,
        date=today
    ).first()

    # Calculate summary statistics
    all_records = Attendance.objects.filter(employee=request.user)
    total_hours = sum(record.hours_worked() for record in all_records)
    absent_days = all_records.filter(status="Absent").count()
    half_days = all_records.filter(status="Half Day").count()
    extra_days = all_records.filter(extra_days=True).count()

    user_team = getattr(request.user.profile, 'team', None) if hasattr(request.user, 'profile') else None

    return render(request, "tracker/mark_attendance.html", {
        "already_marked": already_marked,
        "records": records,
        "report": report,
        "today_attendance": today_attendance,
        "total_hours": round(total_hours, 2),
        "absent_days": absent_days,
        "half_days": half_days,
        "extra_days": extra_days,
        "user_team": user_team,
    })


from django.utils.crypto import get_random_string

# =============================
# ✅ ADD EMPLOYEE
# =============================
@staff_member_required
def add_employee(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        team = request.POST.get('team', '')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists.")
            return redirect("admin_dashboard")
            
        password = get_random_string(length=10)
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        EmployeeProfile.objects.create(user=user, team=team if team else None)
        GeneratedCredential.objects.create(user=user, password=password)
        
        messages.success(
            request, 
            f"Successfully created employee! Username: {username} | Auto-generated Password: {password}"
        )
        
    return redirect("admin_dashboard")


# =============================
# ✅ ADMIN DASHBOARD
# =============================
@staff_member_required
def admin_dashboard(request):
    # Filter out staff and superusers from employee list
    users = User.objects.filter(is_staff=False, is_superuser=False)
    
    # Filter handling
    employee_filter = request.GET.get('employee', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    # Filter out staff and superusers from logs
    records_query = Attendance.objects.select_related("employee").filter(
        employee__is_staff=False, 
        employee__is_superuser=False
    ).order_by("-date")
    
    if employee_filter:
        records_query = records_query.filter(employee__username__icontains=employee_filter)
    if start_date:
        records_query = records_query.filter(date__gte=start_date)
    if end_date:
        records_query = records_query.filter(date__lte=end_date)

    records = records_query

    # Fetch corresponding daily reports to display in the view report modal
    reports = DailyReport.objects.filter(date__in=[r.date for r in records], employee__in=[r.employee for r in records])
    report_dict = {(r.employee_id, r.date): r for r in reports}
    
    for r in records:
        report = report_dict.get((r.employee_id, r.date))
        if report:
            report.team_metrics_json = json.dumps(report.team_metrics)
            r.daily_report = report
        else:
            r.daily_report = None

    user_summary = []

    for user in users:
        total = Attendance.objects.filter(employee=user).count()
        present = Attendance.objects.filter(employee=user, status="Present").count()
        absent = Attendance.objects.filter(employee=user, status="Absent").count()
        half_days = Attendance.objects.filter(employee=user, status="Half Day").count()
        extra_days = Attendance.objects.filter(employee=user, extra_days=True).count()
        team = getattr(user.profile, 'team', 'Unassigned') if hasattr(user, 'profile') else 'Unassigned'

        user_summary.append({
            "username": user.username,
            "team": team,
            "total": total,
            "present": present,
            "absent": absent,
            "half_days": half_days,
            "extra_days": extra_days,
        })
        
    recent_creds = GeneratedCredential.objects.select_related('user').order_by('-created_at')

    return render(request, "tracker/admin_dashboard.html", {
        "records": records,
        "user_summary": user_summary,
        "employee_filter": employee_filter,
        "start_date": start_date,
        "end_date": end_date,
        "recent_creds": recent_creds,
    })


# =============================
# ✅ EDIT ATTENDANCE (Admin)
# =============================
@staff_member_required
def edit_attendance(request, record_id):
    if request.method == "POST":
        record = get_object_or_404(Attendance, id=record_id)
        selected_status = request.POST.get("status")
        
        valid_statuses = [choice[0] for choice in Attendance.STATUS_CHOICES]
        if selected_status in valid_statuses:
            record.status = selected_status
        else:
            messages.error(request, "Invalid attendance status.")
            return redirect("admin_dashboard")
        
        check_in_time = request.POST.get("check_in_time")
        check_out_time = request.POST.get("check_out_time")
        extra_days = request.POST.get("extra_days") == "on"

        record.check_in_time = check_in_time if check_in_time else None
        record.check_out_time = check_out_time if check_out_time else None
        record.extra_days = extra_days
        record.save()
        messages.success(request, f"Attendance for {record.employee.username} updated successfully.")
        
    return redirect("admin_dashboard")


# =============================
# ✅ DELETE ATTENDANCE (Admin)
# =============================
@staff_member_required
def delete_attendance(request, record_id):
    if request.method == "POST":
        record = get_object_or_404(Attendance, id=record_id)
        record.delete()
        messages.success(request, "Record deleted successfully.")
    return redirect("admin_dashboard")