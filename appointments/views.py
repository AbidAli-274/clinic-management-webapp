from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView,TemplateView, View, ListView
from accounts.models import UserProfile, Organization
from .models import Consultancy, Session
from .forms import ConsultancyForm, SessionForm  
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import HttpResponse
from datetime import datetime, time, timedelta, date
from calendar import monthrange
import io
import xlsxwriter
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.views.generic import ListView
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from .utils import send_session_creation_notification



class PendingDiscountsListView(LoginRequiredMixin, ListView):
    template_name = 'pending_discounts.html'
    context_object_name = 'items'
    
    def get_queryset(self):
        user = self.request.user
        
        # Check permissions
        if user.role not in ['receptionist', 'admin', 's_admin']:
            return []
        
        # Get both types of pending discounts
        consultancies = Consultancy.objects.filter(status='PendingDiscount')
        sessions = Session.objects.filter(status='PendingDiscount')
        
        # Combine both querysets into a list with type information
        items = []
        for consultancy in consultancies:
            items.append({
                'id': consultancy.pk,
                'type': 'consultancy',
                'object': consultancy,
                'patient_name': consultancy.patient.name,
                # Add other fields you want to display
            })
        
        for session in sessions:
            items.append({
                'id': session.pk,
                'type': 'session',
                'object': session,
                'patient_name': session.patient.name,
                # Add other fields you want to display
            })
            
        return items
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['has_consultancies'] = any(item['type'] == 'consultancy' for item in context['items'])
        context['has_sessions'] = any(item['type'] == 'session' for item in context['items'])
        
        return context
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)

def approve_discount(request, item_type, pk):
    if request.user.role not in ['admin', 's_admin']:
        messages.error(request, "You don't have permission to approve discounts.")
        return redirect('appointments:pending_discounts_list')
    
    if item_type == 'consultancy':
        item = get_object_or_404(Consultancy, pk=pk)
        item.status = 'Pending'
        item.save()
        messages.success(request, f"Discount for Consultancy of {item.patient.name} sb approved.")
    
    elif item_type == 'session':
        item = get_object_or_404(Session, pk=pk)
        item.status = 'Pending'
        item.save()
        messages.success(request, f"Discount for Session of {item.patient.name} sb approved.")
    
    return redirect('appointments:pending_discounts_list')


def reject_discount(request, item_type, pk):
    if request.user.role not in ['admin', 's_admin']:
        messages.error(request, "You don't have permission to reject discounts.")
        return redirect('appointments:pending_discounts_list')
    
    if item_type == 'consultancy':
        item = get_object_or_404(Consultancy, pk=pk)
        patient_name = item.patient.name
        item.delete()
        messages.warning(request, f"Discount for Consultancy of {patient_name} sb has been rejected and deleted.")
    
    elif item_type == 'session':
        item = get_object_or_404(Session, pk=pk)
        patient_name = item.patient.name
        item.delete()
        messages.warning(request, f"Discount for Session of {patient_name} sb has been rejected and deleted.")
    
    return redirect('appointments:pending_discounts_list')


def get_pending_discounts_count(request):
    consultancy_count = Consultancy.objects.filter(status='PendingDiscount').count()
    session_count = Session.objects.filter(status='PendingDiscount').count()
    return JsonResponse({'count': consultancy_count + session_count})


class ConsultancyCreateView(LoginRequiredMixin, CreateView):
    model = Consultancy
    form_class = ConsultancyForm
    template_name = 'consultancy_create.html'
    success_url = reverse_lazy('appointments:consultancy_create') 
    login_url = reverse_lazy('accounts:login') 

    def get_form_kwargs(self):
        # Get the default form kwargs
        kwargs = super().get_form_kwargs()
        # Add the current user to the form kwargs
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not self.request.user.organization:
            messages.error(self.request, "You have no organization to create consultancy.")
            return redirect('appointments:consultancy_create')
        
        if self.request.user.role not in ['admin', 's_admin','receptionist']:
            messages.error(self.request, "You don't have permission to create consultancy.")
            return redirect('appointments:consultancy_create')
        
        form.instance.date_time = timezone.now()

        if form.instance.discount > 0:
            form.instance.status = 'PendingDiscount'
        else:
            form.instance.status = 'Pending'

        messages.success(self.request, "Consultancy Created Successfully!")
        
        return super().form_valid(form)


def get_consultancies(request):
    patient_id = request.GET.get('patient_id')
    consultancies = Consultancy.objects.filter(patient_id=patient_id)
    
    # Convert consultancy instances to a list of dictionaries
    consultancy_data = [{"id": consultancy.id, "name": consultancy.patient.name} for consultancy in consultancies]
    
    return JsonResponse({"consultancies": consultancy_data})


def get_consultancy_fees(request):
    consultancy_id = request.GET.get('consultancy_id')
    
    # Fetch the consultancy instance
    consultancy = Consultancy.objects.filter(id=consultancy_id).first()
    
    # If consultancy is found, return the fee, else return an error message
    if consultancy:
        return JsonResponse({
            'consultancy_fee': consultancy.consultancy_fee  # Return the consultancy fee
        })
    else:
        return JsonResponse({
            'error': 'Consultancy not found'
        }, status=404)


class SessionCreateView(LoginRequiredMixin, CreateView):
    model = Session
    form_class = SessionForm
    template_name = 'session_create.html'
    success_url = reverse_lazy('appointments:session_create')  
    login_url = reverse_lazy('accounts:login') 

    def get_form_kwargs(self):
        # Get the default form kwargs
        kwargs = super().get_form_kwargs()
        # Add the current user to the form kwargs
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not self.request.user.organization:
            messages.error(self.request, "You have no organization to create session.")
            return redirect('appointments:session_create')
        
        if self.request.user.role not in ['admin', 's_admin','receptionist']:
            messages.error(self.request, "You don't have permission to create session.")
            return redirect('appointments:session_create')
        
        form.instance.date_time = timezone.now()

        if form.instance.further_discount > 0:
            form.instance.status = 'PendingDiscount'
        else:
            form.instance.status = 'Pending'

        messages.success(self.request, "Session Created Successfully!")

        return super().form_valid(form)


class ReportBaseView(LoginRequiredMixin):
  login_url = reverse_lazy('accounts:login')
  
  def get_date_range(self, request):
      # Get report type (daily, weekly, monthly, custom)
      report_type = request.GET.get('report_type', 'daily')
      
      today = timezone.now().date()
      
      if report_type == 'daily':
          # Get specific date or use today
          date_str = request.GET.get('date')
          if date_str:
              try:
                  selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
              except ValueError:
                  selected_date = today
          else:
              selected_date = today
              
          start_date = selected_date
          end_date = selected_date
          date_display = selected_date.strftime('%B %d, %Y')
          
      elif report_type == 'weekly':
          # Get the start of the week (Monday)
          start_of_week = today - timedelta(days=today.weekday())
          
          # Get specific week or use current week
          week_start_str = request.GET.get('week_start')
          if week_start_str:
              try:
                  start_date = datetime.strptime(week_start_str, '%Y-%m-%d').date()
                  # Adjust to start of week (Monday)
                  start_date = start_date - timedelta(days=start_date.weekday())
              except ValueError:
                  start_date = start_of_week
          else:
              start_date = start_of_week
              
          end_date = start_date + timedelta(days=6)
          date_display = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
          
      elif report_type == 'monthly':
          # Get specific month or use current month
          month_str = request.GET.get('month')
          year_str = request.GET.get('year')
          
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
          date_display = start_date.strftime('%B %Y')
          
      elif report_type == 'custom':
          # Get custom date range
          start_date_str = request.GET.get('start_date')
          end_date_str = request.GET.get('end_date')
          
          if start_date_str and end_date_str:
              try:
                  start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                  end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                  
                  # Ensure end_date is not before start_date
                  if end_date < start_date:
                      end_date = start_date
              except ValueError:
                  start_date = today
                  end_date = today
          else:
              start_date = today
              end_date = today
              
          date_display = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
      
      else:  # Default to daily if invalid report_type
          start_date = today
          end_date = today
          date_display = today.strftime('%B %d, %Y')
          report_type = 'daily'
          
      return {
          'start_date': start_date,
          'end_date': end_date,
          'date_display': date_display,
          'report_type': report_type
      }
  
  def categorize_feedback(self, feedback_text):
      if not feedback_text:
          return None
          
      # Define positive and negative keywords
      positive_keywords = ['good', 'great', 'excellent', 'satisfied', 'happy', 'better', 'improved', 'helpful', 'positive', 'thank', 'thanks']
      negative_keywords = ['bad', 'poor', 'not good', 'dissatisfied', 'unhappy', 'worse', 'negative', 'issue', 'problem', 'complaint', 'disappointed']
      
      # Convert to lowercase for case-insensitive matching
      feedback_lower = feedback_text.lower()
      
      # Count positive and negative matches
      positive_count = sum(1 for word in positive_keywords if word in feedback_lower)
      negative_count = sum(1 for word in negative_keywords if word in feedback_lower)
      
      # Determine feedback type
      if positive_count > 0 and negative_count > 0:
          return 'mixed'
      elif positive_count > 0:
          return 'positive'
      elif negative_count > 0:
          return 'negative'
      else:
          return 'neutral'  # Default if no keywords match
  
  def get_report_data(self, start_date, end_date, feedback_filter=None, organization_name=None, user=None):
    # Set time range for the selected dates
    date_start = datetime.combine(start_date, time.min)
    date_end = datetime.combine(end_date, time.max)
    
    # Get consultancies for the date range
    consultancies = Consultancy.objects.filter(
        date_time__range=(date_start, date_end)
    ).select_related('patient', 'referred_doctor')

    print("consultancies----",consultancies)
    
    # Get sessions for the date range
    sessions = Session.objects.filter(
        date_time__range=(date_start, date_end)
    ).select_related('patient', 'doctor', 'consultancy')
    print("sessions----",sessions)

    # Handle organization filter
    if organization_name:
        print("--------1")
        # Get organization instance based on name
        organization = Organization.objects.get(id=organization_name)
        
        # Filter consultancies and sessions by the organization
        consultancies = consultancies.filter(patient__organization=organization)
        sessions = sessions.filter(patient__organization=organization)
    
    elif user and user.organization:
        # If no organization_name but user has an organization, filter by user's organization
        consultancies = consultancies.filter(
            patient__organization=user.organization)
        sessions = sessions.filter(patient__organization=user.organization)
    
    # Calculate statistics
    total_consultancies = consultancies.count()
    total_sessions = sessions.count()
    
    # Calculate financial data
    consultancy_revenue = consultancies.aggregate(
        total=Sum('consultancy_fee'),
        discount=Sum('discount')
    )
    
    session_revenue = sessions.aggregate(
        total=Sum('session_fee')
    )
    
    total_revenue = (consultancy_revenue['total'] or 0) + (session_revenue['total'] or 0)
    total_discount = consultancy_revenue['discount'] or 0
    
    # Get status counts
    consultancy_status = {
        'pending': consultancies.filter(status='Pending').count(),
        'continue': consultancies.filter(status='Continue').count(),
        'completed': consultancies.filter(status='Completed').count(),
    }
    
    session_status = {
        'pending': sessions.filter(status='Pending').count(),
        'continue': sessions.filter(status='Continue').count(),
        'completed': sessions.filter(status='Completed').count(),
    }
    
    # Prepare patient history data
    patient_history = []
    
    # Process consultancies for patient history
    for consultancy in consultancies:
        # Skip if feedback filter is applied and doesn't match
        if feedback_filter and feedback_filter != self.categorize_feedback(consultancy.chief_complaint):
            continue
          
        patient_history.append({
            'type': 'Consultancy',
            'id': consultancy.id,
            'patient_name': consultancy.patient.name,
            'patient_id': consultancy.patient.id,
            'phone': consultancy.patient.phone_number,
            'gender': consultancy.patient.gender,
            'time': consultancy.date_time.strftime('%H:%M'),
            'date': consultancy.date_time.strftime('%Y-%m-%d'),
            'doctor': consultancy.referred_doctor if consultancy.referred_doctor else 'N/A',
            'amount': float(consultancy.consultancy_fee),
            'discount': float(consultancy.discount),
            'net_amount': float(consultancy.consultancy_fee) - float(consultancy.discount),
            'status': consultancy.status,
            'chief_complaint': consultancy.chief_complaint,
            'sessions': consultancy.number_of_sessions,
            'feedback_type': self.categorize_feedback(consultancy.chief_complaint)
        })
    
    # Process sessions for patient history
    for session in sessions:
        # Skip if feedback filter is applied and doesn't match
        if feedback_filter and feedback_filter != self.categorize_feedback(session.feedback):
            continue
          
        patient_history.append({
            'type': 'Session',
            'id': session.id,
            'patient_name': session.patient.name,
            'patient_id': session.patient.id,
            'phone': session.patient.phone_number,
            'gender': session.patient.gender,
            'time': session.date_time.strftime('%H:%M'),
            'date': session.date_time.strftime('%Y-%m-%d'),
            'doctor': session.doctor if session.doctor else 'N/A',
            'amount': float(session.session_fee),
            'discount': 0,
            'net_amount': float(session.session_fee),
            'status': session.status,
            'feedback': session.feedback,
            'consultancy_id': session.consultancy.id if session.consultancy else None,
            'feedback_type': self.categorize_feedback(session.feedback)
        })
    
    # Sort patient history by date and time
    patient_history.sort(key=lambda x: (x['date'], x['time']))
    
    return {
        'total_consultancies': total_consultancies,
        'total_sessions': total_sessions,
        'total_appointments': total_consultancies + total_sessions,
        'total_revenue': total_revenue,
        'total_discount': total_discount,
        'net_revenue': total_revenue - total_discount,
        'consultancy_status': consultancy_status,
        'session_status': session_status,
        'patient_history': patient_history,
    }


class DailyReportView(ReportBaseView, TemplateView):
    template_name = 'daily_report.html'
    paginate_by = 15  # Number of records per page

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to check for admin permission."""
        if not request.user.is_authenticated or request.user.role != 's_admin':
            raise PermissionDenied("You do not have permission to view reports.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range based on request parameters
        date_range = self.get_date_range(self.request)
        start_date = date_range['start_date']
        end_date = date_range['end_date']

        print("start_date---",start_date)
        print("end_date---",end_date)
        
        # Get feedback filter if provided
        feedback_filter = self.request.GET.get('feedback_filter', '')
        
        # Get organization filter if provided
        organization_id = self.request.GET.get('organization_id', '')
    
        organizations = Organization.objects.all().order_by('name')
        
        # Get report data, passing the current user
        report_data = self.get_report_data(
            start_date, 
            end_date, 
            feedback_filter if feedback_filter else None,
            organization_id if organization_id else None,
            self.request.user  # Pass the current user
        )
        print("report_data-------",report_data)
        
        # Pagination for patient history
        patient_history = report_data['patient_history']
        page = self.request.GET.get('page', 1)
        paginator = Paginator(patient_history, self.paginate_by)
        
        try:
            paginated_history = paginator.page(page)
        except PageNotAnInteger:
            paginated_history = paginator.page(1)
        except EmptyPage:
            paginated_history = paginator.page(paginator.num_pages)
        
        # Get date navigation for UI
        today = timezone.now().date()
        
        if date_range['report_type'] == 'daily':
            prev_date = start_date - timedelta(days=1)
            next_date = start_date + timedelta(days=1)
            prev_url = f"?report_type=daily&date={prev_date.strftime('%Y-%m-%d')}"
            next_url = f"?report_type=daily&date={next_date.strftime('%Y-%m-%d')}"
        elif date_range['report_type'] == 'weekly':
            prev_week = start_date - timedelta(days=7)
            next_week = start_date + timedelta(days=7)
            prev_url = f"?report_type=weekly&week_start={prev_week.strftime('%Y-%m-%d')}"
            next_url = f"?report_type=weekly&week_start={next_week.strftime('%Y-%m-%d')}"
        elif date_range['report_type'] == 'monthly':
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
                
            prev_url = f"?report_type=monthly&month={prev_month.month}&year={prev_month.year}"
            next_url = f"?report_type=monthly&month={next_month.month}&year={next_month.year}"
        else:  # Custom - no navigation
            prev_url = None
            next_url = None
        
        # Update report_data to use paginated history
        report_data['patient_history'] = paginated_history
        
        context.update({
            'selected_date': start_date,
            'end_date': end_date,
            'selected_date_display': date_range['date_display'],
            'report_type': date_range['report_type'],
            'prev_url': prev_url,
            'next_url': next_url,
            'paginator': paginator,
            'page_obj': paginated_history,
            'feedback_filter': feedback_filter,
            'organization_id': organization_id,
            'organizations': organizations,
            **report_data
        })
        
        return context
    

class ExportPDFView(ReportBaseView, View):
    def get(self, request, *args, **kwargs):
        # Get date range based on request parameters
        date_range = self.get_date_range(request)
        start_date = date_range['start_date']
        end_date = date_range['end_date']
        
        # Get report data
        report_data = self.get_report_data(start_date, end_date)
        
        # Create a file-like buffer to receive PDF data
        buffer = io.BytesIO()
        
        # Create the PDF object, using the buffer as its "file"
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        subtitle_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Add title
        elements.append(Paragraph(f"Clinic Report: {date_range['date_display']}", title_style))
        elements.append(Spacer(1, 12))
        
        # Add summary statistics
        elements.append(Paragraph("Summary Statistics", subtitle_style))
        elements.append(Spacer(1, 6))
        
        summary_data = [
            ["Total Appointments", "Total Revenue", "Total Discount", "Net Revenue"],
            [
                str(report_data['total_appointments']),
                f"₹{report_data['total_revenue']:.2f}",
                f"₹{report_data['total_discount']:.2f}",
                f"₹{report_data['net_revenue']:.2f}"
            ]
        ]
        
        summary_table = Table(summary_data, colWidths=[120, 120, 120, 120])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 12))
        
        # Add patient history
        elements.append(Paragraph("Patient History", subtitle_style))
        elements.append(Spacer(1, 6))
        
        # Table header
        history_data = [
            ["Patient", "Type", "Date", "Time", "Doctor", "Amount", "Discount", "Net", "Status"]
        ]
        
        # Add patient history rows
        for entry in report_data['patient_history']:
            history_data.append([
                entry['patient_name'],
                entry['type'],
                entry['date'],
                entry['time'],
                entry['doctor'],
                f"₹{entry['amount']:.2f}",
                f"₹{entry['discount']:.2f}",
                f"₹{entry['net_amount']:.2f}",
                entry['status']
            ])
        
        history_table = Table(history_data, colWidths=[80, 60, 70, 50, 80, 60, 60, 60, 60])
        history_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8)
        ]))
        
        elements.append(history_table)
        
        # Build the PDF
        doc.build(elements)
        
        # Get the value of the BytesIO buffer
        pdf = buffer.getvalue()
        buffer.close()
        
        # Create the HTTP response
        response = HttpResponse(content_type='application/pdf')
        filename = f"clinic_report_{start_date.strftime('%Y%m%d')}"
        if start_date != end_date:
            filename += f"_to_{end_date.strftime('%Y%m%d')}"
        response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        
        # Write the PDF to the response
        response.write(pdf)
        return response


class ExportExcelView(ReportBaseView, View):
    def get(self, request, *args, **kwargs):
        # Get date range based on request parameters
        date_range = self.get_date_range(request)
        start_date = date_range['start_date']
        end_date = date_range['end_date']
        
        # Get report data
        report_data = self.get_report_data(start_date, end_date)
        
        # Create a file-like buffer to receive Excel data
        buffer = io.BytesIO()
        
        # Create Excel workbook and add a worksheet
        workbook = xlsxwriter.Workbook(buffer)
        summary_sheet = workbook.add_worksheet('Summary')
        history_sheet = workbook.add_worksheet('Patient History')
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#B8CCE4',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'border': 1
        })
        
        money_format = workbook.add_format({
            'border': 1,
            'num_format': '₹#,##0.00'
        })
        
        # Write title to summary sheet
        summary_sheet.write(0, 0, f"Clinic Report: {date_range['date_display']}", header_format)
        summary_sheet.merge_range(0, 0, 0, 3, f"Clinic Report: {date_range['date_display']}", header_format)
        
        # Write summary statistics headers
        summary_sheet.write(2, 0, "Total Appointments", header_format)
        summary_sheet.write(2, 1, "Total Revenue", header_format)
        summary_sheet.write(2, 2, "Total Discount", header_format)
        summary_sheet.write(2, 3, "Net Revenue", header_format)
        
        # Write summary statistics data
        summary_sheet.write(3, 0, report_data['total_appointments'], cell_format)
        summary_sheet.write(3, 1, report_data['total_revenue'], money_format)
        summary_sheet.write(3, 2, report_data['total_discount'], money_format)
        summary_sheet.write(3, 3, report_data['net_revenue'], money_format)
        
        # Write status breakdown headers
        summary_sheet.write(5, 0, "Status", header_format)
        summary_sheet.write(5, 1, "Consultancies", header_format)
        summary_sheet.write(5, 2, "Sessions", header_format)
        summary_sheet.write(5, 3, "Total", header_format)
        
        # Write status breakdown data
        statuses = ['pending', 'continue', 'completed']
        for i, status in enumerate(statuses):
            row = 6 + i
            consultancy_count = report_data['consultancy_status'][status]
            session_count = report_data['session_status'][status]
            
            summary_sheet.write(row, 0, status.capitalize(), cell_format)
            summary_sheet.write(row, 1, consultancy_count, cell_format)
            summary_sheet.write(row, 2, session_count, cell_format)
            summary_sheet.write(row, 3, consultancy_count + session_count, cell_format)
        
        # Set column widths for summary sheet
        summary_sheet.set_column(0, 0, 20)
        summary_sheet.set_column(1, 3, 15)
        
        # Write patient history headers
        history_headers = ["Patient", "Type", "Date", "Time", "Doctor", "Amount", "Discount", "Net", "Status"]
        for col, header in enumerate(history_headers):
            history_sheet.write(0, col, header, header_format)
        
        # Write patient history data
        for row, entry in enumerate(report_data['patient_history']):
            # Extract the patient name (if it's a UserProfile object)
            patient_name = entry['patient_name'].username if isinstance(entry['patient_name'], UserProfile) else entry['patient_name']
            
            # Extract the doctor's name (if it's a UserProfile object)
            doctor_name = entry['doctor'].username if isinstance(entry['doctor'], UserProfile) else entry['doctor']
            
            # Now write the values to the worksheet
            history_sheet.write(row + 1, 0, patient_name, cell_format)
            history_sheet.write(row + 1, 1, entry['type'], cell_format)
            history_sheet.write(row + 1, 2, entry['date'], cell_format)
            history_sheet.write(row + 1, 3, entry['time'], cell_format)
            history_sheet.write(row + 1, 4, doctor_name, cell_format)  # Use the doctor's username here
            history_sheet.write(row + 1, 5, entry['amount'], money_format)
            history_sheet.write(row + 1, 6, entry['discount'], money_format)
            history_sheet.write(row + 1, 7, entry['net_amount'], money_format)
            history_sheet.write(row + 1, 8, entry['status'], cell_format)

        
        # Set column widths for history sheet
        history_sheet.set_column(0, 0, 20)  # Patient name
        history_sheet.set_column(1, 1, 12)  # Type
        history_sheet.set_column(2, 2, 12)  # Date
        history_sheet.set_column(3, 3, 8)   # Time
        history_sheet.set_column(4, 4, 20)  # Doctor
        history_sheet.set_column(5, 7, 12)  # Amount columns
        history_sheet.set_column(8, 8, 12)  # Status
        
        # Close the workbook
        workbook.close()
        
        # Get the value of the BytesIO buffer
        excel_data = buffer.getvalue()
        buffer.close()
        
        # Create the HTTP response
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f"clinic_report_{start_date.strftime('%Y%m%d')}"
        if start_date != end_date:
            filename += f"_to_{end_date.strftime('%Y%m%d')}"
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        
        # Write the Excel data to the response
        response.write(excel_data)
        return response


def trigger_home_refresh(request):
    """Trigger a refresh of the home screen data."""
    # This endpoint doesn't need to return anything
    # It's just a signal to refresh the home screen
    return JsonResponse({'status': 'success'})

