from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User

from .models import Attendance, DailyReport


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
            "today_actions": "",
            "outcomes": "",
            "weekly_plan": "",
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
            report.today_actions = request.POST.get("today_actions", "")
            report.outcomes = request.POST.get("outcomes", "")
            report.weekly_plan = request.POST.get("weekly_plan", "")
            report.dau_metric = request.POST.get("dau_metric", "")
            report.grades_qa = request.POST.get("grades_qa", "")
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

    return render(request, "tracker/mark_attendance.html", {
        "already_marked": already_marked,
        "records": records,
        "report": report,
        "today_attendance": today_attendance,
        "total_hours": round(total_hours, 2),
        "absent_days": absent_days,
        "half_days": half_days,
        "extra_days": extra_days,
    })


# =============================
# ✅ REGISTER USER
# =============================
def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = UserCreationForm()

    return render(request, "tracker/register.html", {"form": form})


# =============================
# ✅ ADMIN DASHBOARD
# =============================
@staff_member_required
def admin_dashboard(request):
    # Filter out staff and superusers from employee list
    users = User.objects.filter(is_staff=False, is_superuser=False)
    
    # Filter handling
    employee_filter = request.GET.get('employee', '').strip()
    date_filter = request.GET.get('date', '').strip()

    # Filter out staff and superusers from logs
    records_query = Attendance.objects.select_related("employee").filter(
        employee__is_staff=False, 
        employee__is_superuser=False
    ).order_by("-date")
    
    if employee_filter:
        records_query = records_query.filter(employee__username__icontains=employee_filter)
    if date_filter:
        records_query = records_query.filter(date=date_filter)

    records = records_query

    # Fetch corresponding daily reports to display in the view report modal
    reports = DailyReport.objects.filter(date__in=[r.date for r in records], employee__in=[r.employee for r in records])
    report_dict = {(r.employee_id, r.date): r for r in reports}
    
    for r in records:
        r.daily_report = report_dict.get((r.employee_id, r.date))

    user_summary = []

    for user in users:
        total = Attendance.objects.filter(employee=user).count()
        present = Attendance.objects.filter(employee=user, status="Present").count()
        absent = Attendance.objects.filter(employee=user, status="Absent").count()
        half_days = Attendance.objects.filter(employee=user, status="Half Day").count()
        extra_days = Attendance.objects.filter(employee=user, extra_days=True).count()

        user_summary.append({
            "username": user.username,
            "total": total,
            "present": present,
            "absent": absent,
            "half_days": half_days,
            "extra_days": extra_days,
        })

    return render(request, "tracker/admin_dashboard.html", {
        "records": records,
        "user_summary": user_summary,
        "employee_filter": employee_filter,
        "date_filter": date_filter,
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