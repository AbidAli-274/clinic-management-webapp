import io
from calendar import monthrange
from datetime import date, datetime, time, timedelta

import xlsxwriter
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import IntegrityError
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, View
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from accounts.models import Organization, UserProfile

from .forms import ConsultancyForm, ReceptionistConsultancyForm, SessionForm
from .models import Consultancy, Session, RecordLog
from .utils import (
    send_session_creation_notification,
    create_consultancy_record_log,
    create_session_record_log,
    update_consultancy_record_log,
    update_session_record_log,
    delete_record_log,
    create_advance_record_log,
    categorize_feedback,
)


class PendingDiscountsListView(LoginRequiredMixin, ListView):
    template_name = "pending_discounts.html"
    context_object_name = "items"

    def get_queryset(self):
        user = self.request.user

        # Check permissions
        if user.role not in ["receptionist", "admin", "s_admin"]:
            return []

        # Get both types of pending discounts
        consultancies = Consultancy.objects.filter(status="PendingDiscount")
        sessions = Session.objects.filter(status="PendingDiscount")

        # Combine both querysets into a list with type information
        items = []
        for consultancy in consultancies:
            # Get advance payment information for this consultancy
            advance_record = RecordLog.objects.filter(
                consultancy=consultancy, record_type="advance"
            ).first()

            items.append(
                {
                    "id": consultancy.pk,
                    "type": "consultancy",
                    "object": consultancy,
                    "patient_name": consultancy.patient.name,
                    "advance_amount": (
                        advance_record.net_amount if advance_record else 0
                    ),
                    "paid_sessions": (
                        advance_record.chief_complaint if advance_record else 0
                    ),  # chief_complaint stores paid sessions
                    "total_sessions": (
                        advance_record.number_of_sessions if advance_record else 0
                    ),  # number_of_sessions stores total sessions
                    "record_discount": advance_record.discount if advance_record else 0,
                }
            )

        for session in sessions:
            items.append(
                {
                    "id": session.pk,
                    "type": "session",
                    "object": session,
                    "patient_name": session.patient.name,
                    "record_discount": (
                        session.further_discount if session.further_discount else 0
                    ),
                    # Add other fields you want to display
                }
            )

        return items

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["has_consultancies"] = any(
            item["type"] == "consultancy" for item in context["items"]
        )
        context["has_sessions"] = any(
            item["type"] == "session" for item in context["items"]
        )

        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        return super().dispatch(request, *args, **kwargs)


def approve_discount(request, item_type, pk):
    if request.user.role not in ["admin", "s_admin"]:
        messages.error(request, "You don't have permission to approve discounts.")
        return redirect("appointments:pending_discounts_list")

    if item_type == "consultancy":
        item = get_object_or_404(Consultancy, pk=pk)
        item.status = "Completed"
        item.save()

        # Update record log entry
        try:
            update_consultancy_record_log(item)
        except Exception as e:
            print(f"Error updating record log for consultancy {item.id}: {e}")

        messages.success(
            request, f"Discount for Consultancy of {item.patient.name} sb approved."
        )

    elif item_type == "session":
        item = get_object_or_404(Session, pk=pk)
        item.status = "Pending"
        item.save()

        # Update record log entry
        try:
            update_session_record_log(item)
        except Exception as e:
            print(f"Error updating record log for session {item.id}: {e}")

        messages.success(
            request, f"Discount for Session of {item.patient.name} sb approved."
        )

    return redirect("appointments:pending_discounts_list")


def reject_discount(request, item_type, pk):
    if request.user.role not in ["admin", "s_admin"]:
        messages.error(request, "You don't have permission to reject discounts.")
        return redirect("appointments:pending_discounts_list")

    if item_type == "consultancy":
        item = get_object_or_404(Consultancy, pk=pk)
        patient_name = item.patient.name

        # Delete record log entry first
        try:
            delete_record_log("consultancy", item.id)
        except Exception as e:
            print(f"Error deleting record log for consultancy {item.id}: {e}")

        item.delete()
        messages.warning(
            request,
            f"Discount for Consultancy of {patient_name} sb has been rejected and deleted.",
        )

    elif item_type == "session":
        item = get_object_or_404(Session, pk=pk)
        patient_name = item.patient.name

        # Delete record log entry first
        try:
            delete_record_log("session", item.id)
        except Exception as e:
            print(f"Error deleting record log for session {item.id}: {e}")

        item.delete()
        messages.warning(
            request,
            f"Discount for Session of {patient_name} sb has been rejected and deleted.",
        )

    return redirect("appointments:pending_discounts_list")


def get_pending_discounts_count(request):
    consultancy_count = Consultancy.objects.filter(status="PendingDiscount").count()
    session_count = Session.objects.filter(status="PendingDiscount").count()
    return JsonResponse({"count": consultancy_count + session_count})


class ConsultancyCreateView(LoginRequiredMixin, CreateView):
    model = Consultancy
    form_class = ConsultancyForm
    template_name = "consultancy_create.html"
    success_url = reverse_lazy("appointments:consultancy_create")
    login_url = reverse_lazy("accounts:login")

    def get_form_kwargs(self):
        # Get the default form kwargs
        kwargs = super().get_form_kwargs()
        # Add the current user to the form kwargs
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not self.request.user.organization:
            messages.error(
                self.request, "You have no organization to create consultancy."
            )
            return redirect("appointments:consultancy_create")

        if self.request.user.role not in ["admin", "s_admin", "receptionist"]:
            messages.error(
                self.request, "You don't have permission to create consultancy."
            )
            return redirect("appointments:consultancy_create")

        form.instance.date_time = timezone.now()
        form.instance.status = "Pending"

        # if form.instance.discount and form.instance.discount > 0:
        #     form.instance.status = "PendingDiscount"
        # else:
        #     form.instance.status = "Pending"

        # Save the consultancy first
        consultancy = form.save()

        # Create record log entry
        try:
            create_consultancy_record_log(consultancy)
        except Exception as e:
            # Log the error but don't fail the consultancy creation
            print(f"Error creating record log for consultancy {consultancy.id}: {e}")

        messages.success(self.request, "Consultancy Created Successfully!")

        return super().form_valid(form)


def get_consultancies(request):
    patient_id = request.GET.get("patient_id")
    consultancies = Consultancy.objects.filter(
        patient_id=patient_id, status="Completed"
    )

    # Convert consultancy instances to a list of dictionaries
    consultancy_data = []
    for consultancy in consultancies:
        # Count completed sessions for this consultancy
        completed_sessions = Session.objects.filter(
            consultancy=consultancy,
        ).count()

        # Convert UTC time to local timezone
        local_time = timezone.localtime(consultancy.date_time)

        consultancy_data.append(
            {
                "id": consultancy.id,
                "patient_name": consultancy.patient.name,
                "date_time": local_time.isoformat(),
                "completed_sessions": completed_sessions,
                "total_sessions": consultancy.number_of_sessions,
            }
        )

    return JsonResponse({"consultancies": consultancy_data})


class SessionCreateView(LoginRequiredMixin, CreateView):
    model = Session
    form_class = SessionForm
    template_name = "session_create.html"
    success_url = reverse_lazy("appointments:session_create")
    login_url = reverse_lazy("accounts:login")

    def get_form_kwargs(self):
        # Get the default form kwargs
        kwargs = super().get_form_kwargs()
        # Add the current user to the form kwargs
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not self.request.user.organization:
            messages.error(self.request, "You have no organization to create session.")
            return redirect("appointments:session_create")

        if self.request.user.role not in ["admin", "s_admin", "receptionist"]:
            messages.error(self.request, "You don't have permission to create session.")
            return redirect("appointments:session_create")

        # Get the selected consultancy
        consultancy = form.cleaned_data.get("consultancy")
        # Check if we've reached the session limit
        if consultancy.status == "SessionEnded":
            messages.error(
                self.request,
                f"Cannot create more sessions. Sessions has beed ended by doctor for this patient.",
            )
            return redirect("appointments:session_create")

        # Check if there's already a pending or continue session for this consultancy
        existing_session = Session.objects.filter(
            consultancy=consultancy, status__in=["Pending", "Continue"]
        ).first()

        if existing_session:
            messages.error(
                self.request,
                f"Cannot create another session. Patient {consultancy.patient.name} already has a {existing_session.status.lower()} session for this consultancy.",
            )
            return redirect("appointments:session_create")

        # Check if patient has already paid for all sessions
        total_created_sessions = Session.objects.filter(consultancy=consultancy).count()
        total_paid_sessions = consultancy.paid_sessions or 0
        total_number_sessions = consultancy.number_of_sessions or 0

        # If paid sessions are greater than or equal to total sessions, set session fee to 0
        if total_paid_sessions >= total_created_sessions:
            form.instance.session_fee = 0
            messages.info(
                self.request,
                f"Session fee set to 0. Patient has already paid from {total_number_sessions} sessions (paid: {total_paid_sessions}).",
            )

        # Create a unique key for this submission to prevent duplicates
        patient = form.cleaned_data.get("patient")
        submission_key = f"session_submission_{patient.id}_{consultancy.id}_{int(timezone.now().timestamp())}"

        if self.request.session.get(submission_key):
            messages.warning(
                self.request,
                "This session has already been created. Please check the sessions list.",
            )
            return redirect("appointments:session_create")

        form.instance.date_time = timezone.now()

        # Get the further discount amount from the form
        further_discount = form.cleaned_data.get("further_discount") or 0

        # Add the further discount to the consultancy's discount field
        if further_discount > 0:
            consultancy.discount = (consultancy.discount or 0) + further_discount
            consultancy.save()

        # Set the session's further discount to the original further discount amount
        form.instance.further_discount = further_discount

        if further_discount > 0:
            form.instance.status = "PendingDiscount"
        else:
            form.instance.status = "Pending"

        try:
            # Save the session
            session = form.save()

            # Create record log entry
            try:
                create_session_record_log(session)
            except Exception as e:
                # Log the error but don't fail the session creation
                print(f"Error creating record log for session {session.id}: {e}")

            # Mark this submission as processed
            self.request.session[submission_key] = True

            # Clean up old submission keys (keep only last 10)
            submission_keys = [
                k
                for k in self.request.session.keys()
                if k.startswith("session_submission_")
            ]
            if len(submission_keys) > 10:
                for old_key in submission_keys[:-10]:
                    del self.request.session[old_key]

            messages.success(self.request, "Session Created Successfully!")

        except IntegrityError:
            # Handle database constraint violation
            messages.error(
                self.request,
                "A session for this patient and consultancy already exists at this time. "
                "Please check if the session was already created.",
            )
            return redirect("appointments:session_create")
        except Exception as e:
            messages.error(
                self.request, f"An error occurred while creating the session: {str(e)}"
            )
            return redirect("appointments:session_create")

        return super().form_valid(form)


class ReportBaseView(LoginRequiredMixin):
    login_url = reverse_lazy("accounts:login")

    def get_date_range(self, request):
        # Get report type (daily, weekly, monthly, custom)
        report_type = request.GET.get("report_type", "daily")

        today = timezone.now().date()

        if report_type == "daily":
            # Get specific date or use today
            date_str = request.GET.get("date")
            if date_str:
                try:
                    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    selected_date = today
            else:
                selected_date = today

            start_date = selected_date
            end_date = selected_date
            date_display = selected_date.strftime("%B %d, %Y")

        elif report_type == "weekly":
            # Get the start of the week (Monday)
            start_of_week = today - timedelta(days=today.weekday())

            # Get specific week or use current week
            week_start_str = request.GET.get("week_start")
            if week_start_str:
                try:
                    start_date = datetime.strptime(week_start_str, "%Y-%m-%d").date()
                    # Adjust to start of week (Monday)
                    start_date = start_date - timedelta(days=start_date.weekday())
                except ValueError:
                    start_date = start_of_week
            else:
                start_date = start_of_week

            end_date = start_date + timedelta(days=6)
            date_display = (
                f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
            )

        elif report_type == "monthly":
            # Get specific month or use current month
            month_str = request.GET.get("month")
            year_str = request.GET.get("year")

            if month_str and year_str:
                try:
                    month = int(month_str)
                    year = int(year_str)
                    if 1 <= month <= 12 and 2000 <= year <= 2100:
                        start_date = date(year, month, 1)
                    else:
                        start_date = date(today.year, today.month, 1)
                except ValueError:
                    start_date = date(today.year, today.month, 1)
            else:
                start_date = date(today.year, today.month, 1)

            # Get the last day of the month
            _, last_day = monthrange(start_date.year, start_date.month)
            end_date = date(start_date.year, start_date.month, last_day)
            date_display = start_date.strftime("%B %Y")

        elif report_type == "custom":
            # Get custom date range
            start_date_str = request.GET.get("start_date")
            end_date_str = request.GET.get("end_date")

            if start_date_str and end_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

                    # Ensure end_date is not before start_date
                    if end_date < start_date:
                        end_date = start_date
                except ValueError:
                    start_date = today
                    end_date = today
            else:
                start_date = today
                end_date = today

            date_display = (
                f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
            )

        else:  # Default to daily if invalid report_type
            start_date = today
            end_date = today
            date_display = today.strftime("%B %d, %Y")
            report_type = "daily"

        return {
            "start_date": start_date,
            "end_date": end_date,
            "date_display": date_display,
            "report_type": report_type,
        }

    def get_report_data(
        self,
        start_date,
        end_date,
        feedback_filter=None,
        organization_name=None,
        user=None,
    ):
        # Set time range for the selected dates
        date_start = datetime.combine(start_date, time.min)
        date_end = datetime.combine(end_date, time.max)

        # Convert to timezone-aware datetime
        date_start = timezone.make_aware(date_start)
        date_end = timezone.make_aware(date_end)

        # Get record logs for the date range
        record_logs = RecordLog.objects.filter(
            date_time__range=(date_start, date_end)
        ).select_related("patient", "doctor", "organization")

        # Handle organization filter
        if organization_name and user.role == "s_admin":
            # Get organization instance based on name
            organization = Organization.objects.get(id=organization_name)
            # Filter record logs by the organization
            record_logs = record_logs.filter(organization=organization)
        elif user.role == "admin":
            # For admin users, always filter by their organization
            record_logs = record_logs.filter(organization=user.organization)
        elif user.organization:
            # For other users with an organization, filter by their organization
            record_logs = record_logs.filter(organization=user.organization)

        # Calculate statistics
        total_consultancies = record_logs.filter(record_type="consultancy").count()
        total_sessions = record_logs.filter(record_type="session").count()

        # Get status counts
        consultancy_status = {
            "pending": record_logs.filter(
                record_type="consultancy", status="Pending"
            ).count(),
            "continue": record_logs.filter(
                record_type="consultancy", status="Continue"
            ).count(),
            "completed": record_logs.filter(
                record_type="consultancy", status="Completed"
            ).count(),
        }

        session_status = {
            "pending": record_logs.filter(
                record_type="session", status="Pending"
            ).count(),
            "continue": record_logs.filter(
                record_type="session", status="Continue"
            ).count(),
            "completed": record_logs.filter(
                record_type="session", status="Completed"
            ).count(),
        }

        # Prepare patient history data
        patient_history = []

        # Process record logs for patient history
        for record_log in record_logs:
            # Skip if feedback filter is applied and doesn't match
            if feedback_filter and feedback_filter != record_log.feedback_type:
                continue

            # Convert UTC time to local timezone
            local_time = timezone.localtime(record_log.date_time)

            # Prepare base data
            history_entry = {
                "type": record_log.record_type.title(),
                "id": record_log.id,
                "patient_name": record_log.patient_name,
                "patient_id": record_log.patient.id,
                "phone": record_log.patient_phone,
                "gender": record_log.patient_gender,
                "time": local_time.strftime("%H:%M"),
                "date": local_time.strftime("%Y-%m-%d"),
                "doctor": record_log.doctor_name,
                "amount": float(record_log.amount),
                "discount": float(record_log.discount),
                "further_discount": float(record_log.further_discount),
                "net_amount": float(record_log.net_amount),
                "status": record_log.status,
                "feedback_type": record_log.feedback_type,
            }

            # Add type-specific fields
            if record_log.record_type == "consultancy":
                history_entry.update(
                    {
                        "chief_complaint": record_log.chief_complaint,
                        "sessions": record_log.number_of_sessions,
                    }
                )
            elif record_log.record_type == "session":
                history_entry.update(
                    {
                        "feedback": record_log.feedback,
                        "consultancy_id": (
                            record_log.consultancy.id
                            if record_log.consultancy
                            else None
                        ),
                    }
                )
            elif record_log.record_type == "advance":
                history_entry.update(
                    {
                        "chief_complaint": record_log.chief_complaint,
                        "sessions": record_log.number_of_sessions,
                    }
                )

            patient_history.append(history_entry)

        # Sort patient history by date and time
        patient_history.sort(key=lambda x: (x["date"], x["time"]))

        # Calculate all amount (sum of all record types for the period)
        total_revenue = record_logs.aggregate(total=Sum("amount"))["total"] or 0
        total_discount = record_logs.aggregate(total=Sum("discount"))["total"] or 0

        return {
            "total_consultancies": total_consultancies,
            "total_sessions": total_sessions,
            "total_appointments": total_consultancies + total_sessions,
            "total_revenue": total_revenue or 0,
            "total_discount": total_discount,
            "net_revenue": total_revenue - total_discount,
            "consultancy_status": consultancy_status,
            "session_status": session_status,
            "patient_history": patient_history,
        }


class DailyReportView(ReportBaseView, TemplateView):
    template_name = "daily_report.html"
    paginate_by = 15  # Number of records per page

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to check for admin or superadmin permission."""
        if not request.user.is_authenticated or request.user.role not in [
            "admin",
            "s_admin",
        ]:
            raise PermissionDenied("You do not have permission to view reports.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get date range based on request parameters
        date_range = self.get_date_range(self.request)
        start_date = date_range["start_date"]
        end_date = date_range["end_date"]

        # Get feedback filter if provided
        feedback_filter = self.request.GET.get("feedback_filter", "")

        # Get organization filter if provided and user is superadmin
        organization_id = None
        organizations = None
        if self.request.user.role == "s_admin":
            organization_id = self.request.GET.get("organization_id", "")
            organizations = Organization.objects.all().order_by("name")

        # Get report data, passing the current user
        report_data = self.get_report_data(
            start_date,
            end_date,
            feedback_filter if feedback_filter else None,
            organization_id if organization_id else None,
            self.request.user,  # Pass the current user
        )

        # Pagination for patient history
        patient_history = report_data["patient_history"]
        page = self.request.GET.get("page", 1)
        paginator = Paginator(patient_history, self.paginate_by)

        try:
            paginated_history = paginator.page(page)
        except PageNotAnInteger:
            paginated_history = paginator.page(1)
        except EmptyPage:
            paginated_history = paginator.page(paginator.num_pages)

        # Get date navigation for UI
        today = timezone.now().date()

        if date_range["report_type"] == "daily":
            prev_date = start_date - timedelta(days=1)
            next_date = start_date + timedelta(days=1)
            prev_url = f"?report_type=daily&date={prev_date.strftime('%Y-%m-%d')}"
            next_url = f"?report_type=daily&date={next_date.strftime('%Y-%m-%d')}"
        elif date_range["report_type"] == "weekly":
            prev_week = start_date - timedelta(days=7)
            next_week = start_date + timedelta(days=7)
            prev_url = (
                f"?report_type=weekly&week_start={prev_week.strftime('%Y-%m-%d')}"
            )
            next_url = (
                f"?report_type=weekly&week_start={next_week.strftime('%Y-%m-%d')}"
            )
        elif date_range["report_type"] == "monthly":
            # Previous month
            if start_date.month == 1:
                prev_month = date(start_date.year - 1, 12, 1)
            else:
                prev_month = date(start_date.year, start_date.month - 1, 1)

            # Next month
            if start_date.month == 12:
                next_month = date(start_date.year + 1, 1, 1)
            else:
                next_month = date(start_date.year, start_date.month + 1, 1)

            prev_url = (
                f"?report_type=monthly&month={prev_month.month}&year={prev_month.year}"
            )
            next_url = (
                f"?report_type=monthly&month={next_month.month}&year={next_month.year}"
            )
        else:  # Custom - no navigation
            prev_url = None
            next_url = None

        # Update report_data to use paginated history
        report_data["patient_history"] = paginated_history

        context.update(
            {
                "selected_date": start_date,
                "end_date": end_date,
                "selected_date_display": date_range["date_display"],
                "report_type": date_range["report_type"],
                "prev_url": prev_url,
                "next_url": next_url,
                "paginator": paginator,
                "page_obj": paginated_history,
                "feedback_filter": feedback_filter,
                "organization_id": organization_id,
                "organizations": organizations,
                "is_superadmin": self.request.user.role == "s_admin",
                **report_data,
            }
        )

        return context


class ExportPDFView(ReportBaseView, View):
    def get(self, request, *args, **kwargs):
        # Get date range based on request parameters
        date_range = self.get_date_range(request)
        start_date = date_range["start_date"]
        end_date = date_range["end_date"]

        # Get report data, passing the current user
        report_data = self.get_report_data(
            start_date, end_date, user=request.user  # Pass the current user
        )

        # Create a file-like buffer to receive PDF data
        buffer = io.BytesIO()

        # Create the PDF object, using the buffer as its "file"
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))

        # Container for the 'Flowable' objects
        elements = []

        # Get styles
        styles = getSampleStyleSheet()
        title_style = styles["Heading1"]
        subtitle_style = styles["Heading2"]
        normal_style = styles["Normal"]

        # Add title
        elements.append(
            Paragraph(f"Clinic Report: {date_range['date_display']}", title_style)
        )
        elements.append(Spacer(1, 12))

        # Add summary statistics
        elements.append(Paragraph("Summary Statistics", subtitle_style))
        elements.append(Spacer(1, 6))

        summary_data = [
            ["Total Appointments", "Total Revenue", "Total Discount", "Net Revenue"],
            [
                str(report_data["total_appointments"]),
                f"₹{report_data['total_revenue']:.2f}",
                f"₹{report_data['total_discount']:.2f}",
                f"₹{report_data['net_revenue']:.2f}",
            ],
        ]

        summary_table = Table(summary_data, colWidths=[120, 120, 120, 120])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        elements.append(summary_table)
        elements.append(Spacer(1, 12))

        # Add patient history
        elements.append(Paragraph("Patient History", subtitle_style))
        elements.append(Spacer(1, 6))

        # Table header
        history_data = [
            [
                "Patient",
                "Type",
                "Date",
                "Time",
                "Doctor",
                "Amount",
                "Discount",
                "Net",
                "Status",
            ]
        ]

        # Add patient history rows
        for entry in report_data["patient_history"]:
            history_data.append(
                [
                    entry["patient_name"],
                    entry["type"],
                    entry["date"],
                    entry["time"],
                    entry["doctor"],
                    f"₹{entry['amount']:.2f}",
                    f"₹{entry['discount']:.2f}",
                    f"₹{entry['net_amount']:.2f}",
                    entry["status"],
                ]
            )

        history_table = Table(
            history_data, colWidths=[80, 60, 70, 50, 80, 60, 60, 60, 60]
        )
        history_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )

        elements.append(history_table)

        # Build the PDF
        doc.build(elements)

        # Get the value of the BytesIO buffer
        pdf = buffer.getvalue()
        buffer.close()

        # Create the HTTP response
        response = HttpResponse(content_type="application/pdf")
        filename = f"clinic_report_{start_date.strftime('%Y%m%d')}"
        if start_date != end_date:
            filename += f"_to_{end_date.strftime('%Y%m%d')}"
        response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'

        # Write the PDF to the response
        response.write(pdf)
        return response


class ExportExcelView(ReportBaseView, View):
    def get(self, request, *args, **kwargs):
        # Get date range based on request parameters
        date_range = self.get_date_range(request)
        start_date = date_range["start_date"]
        end_date = date_range["end_date"]

        # Get report data, passing the current user
        report_data = self.get_report_data(
            start_date, end_date, user=request.user  # Pass the current user
        )

        # Create a file-like buffer to receive Excel data
        buffer = io.BytesIO()

        # Create Excel workbook and add a worksheet
        workbook = xlsxwriter.Workbook(buffer)
        summary_sheet = workbook.add_worksheet("Summary")
        history_sheet = workbook.add_worksheet("Patient History")

        # Add formats
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#B8CCE4", "border": 1}
        )

        cell_format = workbook.add_format({"border": 1})

        money_format = workbook.add_format({"border": 1, "num_format": "₹#,##0.00"})

        # Write title to summary sheet
        summary_sheet.write(
            0, 0, f"Clinic Report: {date_range['date_display']}", header_format
        )
        summary_sheet.merge_range(
            0, 0, 0, 3, f"Clinic Report: {date_range['date_display']}", header_format
        )

        # Write summary statistics headers
        summary_sheet.write(2, 0, "Total Appointments", header_format)
        summary_sheet.write(2, 1, "Total Revenue", header_format)
        summary_sheet.write(2, 2, "Total Discount", header_format)
        summary_sheet.write(2, 3, "Net Revenue", header_format)

        # Write summary statistics data
        summary_sheet.write(3, 0, report_data["total_appointments"], cell_format)
        summary_sheet.write(3, 1, report_data["total_revenue"], money_format)
        summary_sheet.write(3, 2, report_data["total_discount"], money_format)
        summary_sheet.write(3, 3, report_data["net_revenue"], money_format)

        # Write status breakdown headers
        summary_sheet.write(5, 0, "Status", header_format)
        summary_sheet.write(5, 1, "Consultancies", header_format)
        summary_sheet.write(5, 2, "Sessions", header_format)
        summary_sheet.write(5, 3, "Total", header_format)

        # Write status breakdown data
        statuses = ["pending", "continue", "completed"]
        for i, status in enumerate(statuses):
            row = 6 + i
            consultancy_count = report_data["consultancy_status"][status]
            session_count = report_data["session_status"][status]

            summary_sheet.write(row, 0, status.capitalize(), cell_format)
            summary_sheet.write(row, 1, consultancy_count, cell_format)
            summary_sheet.write(row, 2, session_count, cell_format)
            summary_sheet.write(row, 3, consultancy_count + session_count, cell_format)

        # Set column widths for summary sheet
        summary_sheet.set_column(0, 0, 20)
        summary_sheet.set_column(1, 3, 15)

        # Write patient history headers
        history_headers = [
            "Patient",
            "Type",
            "Date",
            "Time",
            "Doctor",
            "Amount",
            "Discount",
            "Net",
            "Status",
        ]
        for col, header in enumerate(history_headers):
            history_sheet.write(0, col, header, header_format)

        # Write patient history data
        for row, entry in enumerate(report_data["patient_history"]):
            # Extract the patient name (if it's a UserProfile object)
            patient_name = (
                entry["patient_name"].username
                if isinstance(entry["patient_name"], UserProfile)
                else entry["patient_name"]
            )

            # Extract the doctor's name (if it's a UserProfile object)
            doctor_name = (
                entry["doctor"].username
                if isinstance(entry["doctor"], UserProfile)
                else entry["doctor"]
            )

            # Now write the values to the worksheet
            history_sheet.write(row + 1, 0, patient_name, cell_format)
            history_sheet.write(row + 1, 1, entry["type"], cell_format)
            history_sheet.write(row + 1, 2, entry["date"], cell_format)
            history_sheet.write(row + 1, 3, entry["time"], cell_format)
            history_sheet.write(
                row + 1, 4, doctor_name, cell_format
            )  # Use the doctor's username here
            history_sheet.write(row + 1, 5, entry["amount"], money_format)
            history_sheet.write(row + 1, 6, entry["discount"], money_format)
            history_sheet.write(row + 1, 7, entry["net_amount"], money_format)
            history_sheet.write(row + 1, 8, entry["status"], cell_format)

        # Set column widths for history sheet
        history_sheet.set_column(0, 0, 20)  # Patient name
        history_sheet.set_column(1, 1, 12)  # Type
        history_sheet.set_column(2, 2, 12)  # Date
        history_sheet.set_column(3, 3, 8)  # Time
        history_sheet.set_column(4, 4, 20)  # Doctor
        history_sheet.set_column(5, 7, 12)  # Amount columns
        history_sheet.set_column(8, 8, 12)  # Status

        # Close the workbook
        workbook.close()

        # Get the value of the BytesIO buffer
        excel_data = buffer.getvalue()
        buffer.close()

        # Create the HTTP response
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename = f"clinic_report_{start_date.strftime('%Y%m%d')}"
        if start_date != end_date:
            filename += f"_to_{end_date.strftime('%Y%m%d')}"
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'

        # Write the Excel data to the response
        response.write(excel_data)
        return response


class ExportDoctorPDFView(LoginRequiredMixin, View):
    login_url = reverse_lazy("accounts:login")

    def get(self, request, *args, **kwargs):
        # Check permissions
        if request.user.role not in ["admin", "s_admin"]:
            raise PermissionDenied("You do not have permission to view reports.")

        # Get selected filters from request
        selected_organization_id = request.GET.get("organization_id")
        selected_doctor_id = request.GET.get("doctor_id")
        selected_month = int(request.GET.get("month", timezone.now().month))
        selected_year = int(request.GET.get("year", timezone.now().year))

        if not selected_doctor_id:
            return HttpResponse("Doctor ID is required", status=400)

        try:
            doctor = UserProfile.objects.get(id=selected_doctor_id, role="doctor")
        except UserProfile.DoesNotExist:
            return HttpResponse("Doctor not found", status=404)

        # Calculate date range for the selected month and year
        start_date = date(selected_year, selected_month, 1)
        if selected_month == 12:
            end_date = date(selected_year + 1, 1, 1)
        else:
            end_date = date(selected_year, selected_month + 1, 1)

        # Use RecordLog for session data
        session_logs = RecordLog.objects.filter(
            doctor=doctor,
            record_type="session",
            date_time__range=(start_date, end_date),
        )
        positive_count = session_logs.filter(feedback_type="positive").count()
        negative_count = session_logs.filter(feedback_type="negative").count()
        mixed_count = session_logs.filter(feedback_type="mixed").count()
        total_sessions = session_logs.filter(status="Completed").count()
        total_feedback = positive_count + negative_count + mixed_count
        if total_feedback > 0:
            satisfaction_percentage = (
                (positive_count + (mixed_count * 0.5)) / total_feedback * 100
            )
        else:
            satisfaction_percentage = 0

        # Use RecordLog for consultancy data
        consultancy_logs = RecordLog.objects.filter(
            doctor=doctor,
            record_type="consultancy",
            date_time__range=(start_date, end_date),
        )
        consultancy_data = []
        for log in consultancy_logs:
            completed_sessions = RecordLog.objects.filter(
                consultancy=log.consultancy, record_type="session", status="Completed"
            ).count()
            completion_percentage = (
                (completed_sessions / log.number_of_sessions * 100)
                if log.number_of_sessions and log.number_of_sessions > 0
                else 0
            )
            consultancy_data.append(
                {
                    "consultancy": log,
                    "recommended_sessions": log.number_of_sessions,
                    "completed_sessions": completed_sessions,
                    "completion_percentage": completion_percentage,
                }
            )

        # Create a file-like buffer to receive PDF data
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        title_style = styles["Heading1"]
        subtitle_style = styles["Heading2"]
        normal_style = styles["Normal"]
        month_name = start_date.strftime("%B %Y")
        elements.append(
            Paragraph(
                f"Doctor Performance Report: {doctor.username} - {month_name}",
                title_style,
            )
        )
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Feedback Statistics", subtitle_style))
        elements.append(Spacer(1, 6))
        feedback_data = [
            ["Feedback Type", "Count"],
            ["Positive Feedback", str(positive_count)],
            ["Mixed Feedback", str(mixed_count)],
            ["Negative Feedback", str(negative_count)],
            ["Total Sessions", str(total_sessions)],
        ]
        feedback_table = Table(feedback_data, colWidths=[200, 100])
        feedback_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        elements.append(feedback_table)
        elements.append(Spacer(1, 12))
        elements.append(
            Paragraph(
                f"Satisfaction Percentage: {satisfaction_percentage:.1f}%",
                subtitle_style,
            )
        )
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Sessions Report", subtitle_style))
        elements.append(Spacer(1, 6))
        sessions_data = [
            [
                "Consultancy Date",
                "Patient",
                "Recommended Sessions",
                "Completed Sessions",
                "Completion %",
            ]
        ]
        for data in consultancy_data:
            sessions_data.append(
                [
                    data["consultancy"].date_time.strftime("%Y-%m-%d"),
                    data["consultancy"].patient_name,
                    str(data["recommended_sessions"]),
                    str(data["completed_sessions"]),
                    f"{data['completion_percentage']:.1f}%",
                ]
            )
        sessions_table = Table(sessions_data, colWidths=[80, 120, 100, 100, 80])
        sessions_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(sessions_table)
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        response = HttpResponse(content_type="application/pdf")
        filename = f"doctor_report_{doctor.username}_{start_date.strftime('%Y%m')}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write(pdf)
        return response


class ExportDoctorExcelView(LoginRequiredMixin, View):
    login_url = reverse_lazy("accounts:login")

    def categorize_feedback(self, feedback_text):
        if not feedback_text:
            return None

        # Define positive and negative keywords
        positive_keywords = [
            "good",
            "great",
            "excellent",
            "satisfied",
            "happy",
            "better",
            "improved",
            "helpful",
            "positive",
            "thank",
            "thanks",
        ]
        negative_keywords = [
            "bad",
            "poor",
            "not good",
            "dissatisfied",
            "unhappy",
            "worse",
            "negative",
            "issue",
            "problem",
            "complaint",
            "disappointed",
        ]
        mixed_keywords = [
            "mixed",
            "neutral",
            "okay",
            "average",
            "satisfactory",
            "ok",
            "partially",
        ]

        # Convert to lowercase for case-insensitive matching
        feedback_lower = feedback_text.lower()

        # Count positive and negative matches
        positive_count = sum(1 for word in positive_keywords if word in feedback_lower)
        negative_count = sum(1 for word in negative_keywords if word in feedback_lower)
        mixed_count = sum(1 for word in mixed_keywords if word in feedback_lower)

        # Determine feedback type
        if positive_count > 0 and negative_count > 0:
            return "mixed"
        elif positive_count > 0:
            return "positive"
        elif negative_count > 0:
            return "negative"
        elif mixed_count > 0:
            return "mixed"
        else:
            return "neutral"

    def get(self, request, *args, **kwargs):
        # Check permissions
        if request.user.role not in ["admin", "s_admin"]:
            raise PermissionDenied("You do not have permission to view reports.")

        # Get selected filters from request
        selected_organization_id = request.GET.get("organization_id")
        selected_doctor_id = request.GET.get("doctor_id")
        selected_month = int(request.GET.get("month", timezone.now().month))
        selected_year = int(request.GET.get("year", timezone.now().year))

        if not selected_doctor_id:
            return HttpResponse("Doctor ID is required", status=400)

        try:
            doctor = UserProfile.objects.get(id=selected_doctor_id, role="doctor")
        except UserProfile.DoesNotExist:
            return HttpResponse("Doctor not found", status=404)

        # Calculate date range for the selected month and year
        start_date = date(selected_year, selected_month, 1)
        if selected_month == 12:
            end_date = date(selected_year + 1, 1, 1)
        else:
            end_date = date(selected_year, selected_month + 1, 1)

        # Use RecordLog for session data
        session_logs = RecordLog.objects.filter(
            doctor=doctor,
            record_type="session",
            date_time__range=(start_date, end_date),
        )
        positive_count = session_logs.filter(feedback_type="positive").count()
        negative_count = session_logs.filter(feedback_type="negative").count()
        mixed_count = session_logs.filter(feedback_type="mixed").count()
        total_sessions = session_logs.filter(status="Completed").count()
        total_feedback = positive_count + negative_count + mixed_count
        if total_feedback > 0:
            satisfaction_percentage = (
                (positive_count + (mixed_count * 0.5)) / total_feedback * 100
            )
        else:
            satisfaction_percentage = 0

        # Use RecordLog for consultancy data
        consultancy_logs = RecordLog.objects.filter(
            doctor=doctor,
            record_type="consultancy",
            date_time__range=(start_date, end_date),
        )
        consultancy_data = []
        for log in consultancy_logs:
            completed_sessions = RecordLog.objects.filter(
                consultancy=log.consultancy, record_type="session", status="Completed"
            ).count()
            completion_percentage = (
                (completed_sessions / log.number_of_sessions * 100)
                if log.number_of_sessions and log.number_of_sessions > 0
                else 0
            )
            consultancy_data.append(
                {
                    "consultancy": log,
                    "recommended_sessions": log.number_of_sessions,
                    "completed_sessions": completed_sessions,
                    "completion_percentage": completion_percentage,
                }
            )

        # Create a file-like buffer to receive Excel data
        buffer = io.BytesIO()

        # Create Excel workbook and add worksheets
        workbook = xlsxwriter.Workbook(buffer)
        summary_sheet = workbook.add_worksheet("Summary")
        sessions_sheet = workbook.add_worksheet("Sessions Report")

        # Add formats
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#B8CCE4", "border": 1}
        )
        cell_format = workbook.add_format({"border": 1})
        percentage_format = workbook.add_format({"border": 1, "num_format": "0.0%"})

        # Write title to summary sheet
        month_name = start_date.strftime("%B %Y")
        summary_sheet.write(
            0,
            0,
            f"Doctor Performance Report: {doctor.username} - {month_name}",
            header_format,
        )
        summary_sheet.merge_range(
            0,
            0,
            0,
            3,
            f"Doctor Performance Report: {doctor.username} - {month_name}",
            header_format,
        )

        # Write feedback statistics headers
        summary_sheet.write(2, 0, "Feedback Type", header_format)
        summary_sheet.write(2, 1, "Count", header_format)

        # Write feedback statistics data
        summary_sheet.write(3, 0, "Positive Feedback", cell_format)
        summary_sheet.write(3, 1, positive_count, cell_format)
        summary_sheet.write(4, 0, "Mixed Feedback", cell_format)
        summary_sheet.write(4, 1, mixed_count, cell_format)
        summary_sheet.write(5, 0, "Negative Feedback", cell_format)
        summary_sheet.write(5, 1, negative_count, cell_format)
        summary_sheet.write(6, 0, "Total Sessions", cell_format)
        summary_sheet.write(6, 1, total_sessions, cell_format)

        # Write satisfaction percentage
        summary_sheet.write(8, 0, "Satisfaction Percentage", header_format)
        summary_sheet.write(8, 1, satisfaction_percentage / 100, percentage_format)

        # Set column widths for summary sheet
        summary_sheet.set_column(0, 0, 25)
        summary_sheet.set_column(1, 1, 15)

        # Write sessions report headers
        sessions_headers = [
            "Consultancy Date",
            "Patient",
            "Recommended Sessions",
            "Completed Sessions",
            "Completion %",
        ]
        for col, header in enumerate(sessions_headers):
            sessions_sheet.write(0, col, header, header_format)

        # Write sessions data
        for row, data in enumerate(consultancy_data):
            sessions_sheet.write(
                row + 1,
                0,
                data["consultancy"].date_time.strftime("%Y-%m-%d"),
                cell_format,
            )
            sessions_sheet.write(
                row + 1, 1, data["consultancy"].patient_name, cell_format
            )
            sessions_sheet.write(row + 1, 2, data["recommended_sessions"], cell_format)
            sessions_sheet.write(row + 1, 3, data["completed_sessions"], cell_format)
            sessions_sheet.write(
                row + 1, 4, data["completion_percentage"] / 100, percentage_format
            )

        # Set column widths for sessions sheet
        sessions_sheet.set_column(0, 0, 15)  # Consultancy Date
        sessions_sheet.set_column(1, 1, 25)  # Patient
        sessions_sheet.set_column(2, 2, 20)  # Recommended Sessions
        sessions_sheet.set_column(3, 3, 20)  # Completed Sessions
        sessions_sheet.set_column(4, 4, 15)  # Completion %

        # Close the workbook
        workbook.close()

        # Get the value of the BytesIO buffer
        excel_data = buffer.getvalue()
        buffer.close()

        # Create the HTTP response
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename = f"doctor_report_{doctor.username}_{start_date.strftime('%Y%m')}.xlsx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        # Write the Excel data to the response
        response.write(excel_data)
        return response


class DoctorReportView(LoginRequiredMixin, TemplateView):
    template_name = "doctor_report.html"
    login_url = reverse_lazy("accounts:login")

    def categorize_feedback(self, feedback_text):
        if not feedback_text:
            return None

        # Define positive and negative keywords
        positive_keywords = [
            "good",
            "great",
            "excellent",
            "satisfied",
            "happy",
            "better",
            "improved",
            "helpful",
            "positive",
            "thank",
            "thanks",
        ]
        negative_keywords = [
            "bad",
            "poor",
            "not good",
            "dissatisfied",
            "unhappy",
            "worse",
            "negative",
            "issue",
            "problem",
            "complaint",
            "disappointed",
        ]
        mixed_keywords = [
            "mixed",
            "neutral",
            "okay",
            "average",
            "satisfactory",
            "ok",
            "partially",
        ]

        # Convert to lowercase for case-insensitive matching
        feedback_lower = feedback_text.lower()

        # Count positive and negative matches
        positive_count = sum(1 for word in positive_keywords if word in feedback_lower)
        negative_count = sum(1 for word in negative_keywords if word in feedback_lower)
        mixed_count = sum(1 for word in mixed_keywords if word in feedback_lower)

        # Determine feedback type
        if positive_count > 0 and negative_count > 0:
            return "mixed"
        elif positive_count > 0:
            return "positive"
        elif negative_count > 0:
            return "negative"
        elif mixed_count > 0:
            return "mixed"
        else:
            return "neutral"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get selected filters from request
        selected_organization_id = self.request.GET.get("organization_id")
        selected_doctor_id = self.request.GET.get("doctor_id")
        selected_month = int(self.request.GET.get("month", timezone.now().month))
        selected_year = int(self.request.GET.get("year", timezone.now().year))

        # Get all organizations
        organizations = Organization.objects.all()
        context["organizations"] = organizations
        context["selected_organization_id"] = selected_organization_id

        # Get doctors based on selected organization
        if selected_organization_id:
            doctors = UserProfile.objects.filter(
                role="doctor", organization_id=selected_organization_id
            )
        else:
            doctors = UserProfile.objects.filter(role="doctor")
        context["doctors"] = doctors

        # Get months and years for dropdowns
        context["months"] = [
            (1, "January"),
            (2, "February"),
            (3, "March"),
            (4, "April"),
            (5, "May"),
            (6, "June"),
            (7, "July"),
            (8, "August"),
            (9, "September"),
            (10, "October"),
            (11, "November"),
            (12, "December"),
        ]
        current_year = timezone.now().year
        context["years"] = range(current_year - 5, current_year + 1)

        # If a doctor is selected, get their data
        if selected_doctor_id:
            try:
                doctor = UserProfile.objects.get(id=selected_doctor_id, role="doctor")
                context["selected_doctor"] = doctor

                # Calculate date range for the selected month and year
                start_date = date(selected_year, selected_month, 1)
                if selected_month == 12:
                    end_date = date(selected_year + 1, 1, 1)
                else:
                    end_date = date(selected_year, selected_month + 1, 1)

                # Get all sessions for the selected doctor in the date range
                sessions = Session.objects.filter(
                    doctor=doctor, date_time__range=(start_date, end_date)
                )

                # Calculate feedback statistics
                positive_count = 0
                negative_count = 0
                mixed_count = 0

                for session in sessions:
                    feedback_category = self.categorize_feedback(session.feedback)
                    if feedback_category == "positive":
                        positive_count += 1
                    elif feedback_category == "negative":
                        negative_count += 1
                    elif feedback_category == "mixed":
                        mixed_count += 1

                total_sessions = sessions.filter(status="Completed").count()
                total_feedback = positive_count + negative_count + mixed_count

                # Calculate satisfaction percentage
                if total_feedback > 0:
                    satisfaction_percentage = (
                        (positive_count + (mixed_count * 0.5)) / total_feedback * 100
                    )
                else:
                    satisfaction_percentage = 0

                # Determine satisfaction color
                if satisfaction_percentage >= 70:
                    satisfaction_color = "green"
                elif satisfaction_percentage >= 40:
                    satisfaction_color = "yellow"
                else:
                    satisfaction_color = "red"

                # Get consultancy data
                consultancies = Consultancy.objects.filter(
                    referred_doctor=doctor, date_time__range=(start_date, end_date)
                ).select_related("patient")

                consultancy_data = []
                for consultancy in consultancies:
                    completed_sessions = Session.objects.filter(
                        consultancy=consultancy, status="Completed"
                    ).count()

                    completion_percentage = (
                        (completed_sessions / consultancy.number_of_sessions * 100)
                        if consultancy.number_of_sessions > 0
                        else 0
                    )

                    consultancy_data.append(
                        {
                            "consultancy": consultancy,
                            "recommended_sessions": consultancy.number_of_sessions,
                            "completed_sessions": completed_sessions,
                            "completion_percentage": completion_percentage,
                        }
                    )

                context.update(
                    {
                        "sessions": sessions,
                        "total_sessions": total_sessions,
                        "positive_feedback": positive_count,
                        "negative_feedback": negative_count,
                        "mixed_feedback": mixed_count,
                        "satisfaction_percentage": satisfaction_percentage,
                        "satisfaction_color": satisfaction_color,
                        "consultancy_data": consultancy_data,
                        "selected_month": selected_month,
                        "selected_year": selected_year,
                    }
                )

            except UserProfile.DoesNotExist:
                messages.error(self.request, "Selected doctor not found.")

        return context


def trigger_home_refresh(request):
    """Trigger a refresh of the home screen data."""
    # This endpoint doesn't need to return anything
    # It's just a signal to refresh the home screen
    return JsonResponse({"status": "success"})


@require_GET
def get_doctors_by_organization(request):
    organization_id = request.GET.get("organization_id")

    if organization_id:
        doctors = UserProfile.objects.filter(
            role="doctor", organization_id=organization_id
        ).values("id", "username")
    else:
        doctors = UserProfile.objects.filter(role="doctor").values("id", "username")

    # Convert QuerySet to list of dictionaries
    doctors_list = list(doctors)

    return JsonResponse({"doctors": doctors_list})


@require_GET
def get_session_feedback_form(request, session_id):
    session = get_object_or_404(Session, id=session_id)

    # Check if user is a room user
    if request.user.role != "room":
        return JsonResponse(
            {"error": "Only room users can provide feedback"}, status=403
        )

    # Check if session is assigned to this room
    if session.room != request.user:
        return JsonResponse(
            {"error": "This session is not assigned to your room"}, status=403
        )

    # Check if session is in progress
    if session.status != "Continue":
        return JsonResponse(
            {"error": "Can only provide feedback for sessions in progress"}, status=403
        )

    # Convert UTC time to local timezone and format
    local_time = timezone.localtime(session.date_time)
    formatted_date = local_time.strftime("%B %d, %Y %I:%M %p")

    return JsonResponse(
        {
            "session_id": session.id,
            "patient_name": session.patient.name,
            "doctor_name": session.doctor.username,
            "date_time": formatted_date,
        }
    )


@require_GET
def submit_session_feedback(request, session_id):
    """Submit feedback for a session."""
    session = get_object_or_404(Session, id=session_id)

    # Check if user is a room user
    if request.user.role != "room":
        return JsonResponse(
            {"error": "Only room users can provide feedback"}, status=403
        )

    # Check if session is assigned to this room
    if session.room != request.user:
        return JsonResponse(
            {"error": "This session is not assigned to your room"}, status=403
        )

    # Check if session is in progress
    if session.status != "Continue":
        return JsonResponse(
            {"error": "Can only provide feedback for sessions in progress"}, status=400
        )

    feedback = request.GET.get("feedback")
    if not feedback or feedback not in ["positive", "negative", "mixed"]:
        return JsonResponse({"error": "Invalid feedback value"}, status=400)

    # Update session with feedback and mark as completed
    session.feedback = feedback
    session.status = "Completed"
    session.save()

    # Update record log entry
    try:
        update_session_record_log(session)
    except Exception as e:
        # Log the error but don't fail the feedback submission
        print(f"Error updating record log for session {session.id}: {e}")

    # Check if this should be the final session
    complete_session = request.GET.get("complete_session", "false").lower() == "true"
    if complete_session:
        # Update the consultancy's status to Completed and set number_of_sessions
        consultancy = session.consultancy
        # Count all completed sessions for this consultancy
        completed_sessions = Session.objects.filter(
            consultancy=consultancy,
        ).count()

        consultancy.status = "SessionEnded"
        consultancy.save()

        # Update consultancy record log
        try:
            update_consultancy_record_log(consultancy)
        except Exception as e:
            # Log the error but don't fail the process
            print(f"Error updating record log for consultancy {consultancy.id}: {e}")

        return JsonResponse(
            {
                "success": True,
                "message": "Feedback submitted successfully and consultancy marked as completed",
            }
        )

    return JsonResponse({"success": True, "message": "Feedback submitted successfully"})


class FeedbackDialogView(LoginRequiredMixin, TemplateView):
    template_name = "feedback_dialog.html"
    login_url = reverse_lazy("accounts:login")

    def get(self, request, *args, **kwargs):
        session_id = kwargs.get("session_id")
        session = get_object_or_404(Session, id=session_id)

        # Check if user is a room user
        if request.user.role != "room":
            raise PermissionDenied("Only room users can provide feedback")

        # Check if session is assigned to this room
        if session.room != request.user:
            raise PermissionDenied("This session is not assigned to your room")

        # Check if session is in progress
        if session.status != "Continue":
            raise PermissionDenied("Can only provide feedback for sessions in progress")

        return super().get(request, *args, **kwargs)


class ReceptionistConsultancyListView(LoginRequiredMixin, ListView):
    model = Consultancy
    template_name = "receptionist_consultancies.html"
    context_object_name = "consultancies"

    def get_queryset(self):
        if self.request.user.role != "receptionist":
            raise PermissionDenied
        return Consultancy.objects.filter(
            status="ReceptionistReview",
            patient__organization=self.request.user.organization,
        )


class ReceptionistConsultancyUpdateView(LoginRequiredMixin, UpdateView):
    model = Consultancy
    form_class = ReceptionistConsultancyForm
    template_name = "consultancy_review.html"
    success_url = reverse_lazy("appointments:receptionist_consultancy_list")

    def get_queryset(self):
        if self.request.user.role != "receptionist":
            raise PermissionDenied
        return Consultancy.objects.filter(
            status="ReceptionistReview",
            patient__organization=self.request.user.organization,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Get the form data
        discount = form.cleaned_data.get("discount", 0) or 0
        paid_sessions = form.cleaned_data.get("paid_sessions", 0) or 0
        total_amount = form.cleaned_data.get("total_amount", 0) or 0
        no_of_sessions = form.cleaned_data.get("number_of_sessions", 0) or 0

        # Get the consultancy instance to access organization
        consultancy = self.get_object()
        default_session_fee = consultancy.patient.organization.default_session_fee

        sessions_fee = paid_sessions * default_session_fee

        # Set status based on discount value
        if discount > 0 or sessions_fee > total_amount:
            form.instance.status = "PendingDiscount"
            messages.success(
                self.request, "Consultancy saved and pending discount approval."
            )
        else:
            form.instance.status = "Completed"
            messages.success(self.request, "Consultancy saved as Completed.")

        # Save the consultancy first
        consultancy = form.save()

        # Update record log entry for consultancy
        try:
            update_consultancy_record_log(consultancy)
        except Exception as e:
            # Log the error but don't fail the consultancy update
            print(f"Error updating record log for consultancy {consultancy.id}: {e}")

        # Create advance record log if paid sessions and total amount are provided
        print(f"DEBUG: paid_sessions={paid_sessions}, total_amount={total_amount}")
        if paid_sessions > 0 and total_amount > 0:
            try:
                print(
                    f"DEBUG: Creating advance record log for consultancy {consultancy.id}"
                )
                create_advance_record_log(
                    consultancy, total_amount, paid_sessions, no_of_sessions
                )
                messages.success(
                    self.request,
                    f"Advance payment record created for {paid_sessions} sessions.",
                )
                print(f"DEBUG: Advance record log created successfully")
            except Exception as e:
                # Log the error but don't fail the form submission
                print(
                    f"Error creating advance record log for consultancy {consultancy.id}: {e}"
                )
                import traceback

                traceback.print_exc()
        else:
            print(
                f"DEBUG: Conditions not met - paid_sessions={paid_sessions}, total_amount={total_amount}"
            )

        return super().form_valid(form)


@require_GET
def get_doctor_by_consultancy(request):
    consultancy_id = request.GET.get("consultancy_id")
    consultancy = get_object_or_404(Consultancy, id=consultancy_id)
    doctor = consultancy.referred_doctor

    # Get paid sessions and total sessions
    paid_sessions = consultancy.paid_sessions or 0
    total_sessions = Session.objects.filter(consultancy=consultancy).count()

    if doctor:
        return JsonResponse(
            {
                "doctor_id": doctor.pk,
                "doctor_name": doctor.username,
                "discount": str(consultancy.discount or 0),
                "paid_sessions": paid_sessions,
                "total_sessions": total_sessions,
            }
        )
    else:
        return JsonResponse(
            {
                "doctor_id": "",
                "doctor_name": "",
                "discount": "0",
                "paid_sessions": paid_sessions,
                "total_sessions": total_sessions,
            }
        )
