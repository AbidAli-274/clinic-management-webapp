from .models import Consultancy, Session
from django.utils import timezone
from datetime import datetime, time
from .models import Session, Consultancy
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def send_session_creation_notification(consultancy):
        """Broadcast the new session creation to all WebSocket clients."""
        channel_layer = get_channel_layer()
        group_name = "presence_group"

        # Get today's date with time set to beginning of day
        today = timezone.now().date()
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)
        
        # Get pending and continue sessions for today
        pending_sessions = Session.objects.filter(
            date_time__range=(today_start, today_end),
            status='Pending'
        ).select_related('patient')
        
        in_progress_sessions = Session.objects.filter(
            date_time__range=(today_start, today_end),
            status='Continue'
        ).select_related('patient')
        
        # Get pending and continue consultancies for today
        pending_consultancies = Consultancy.objects.filter(
            date_time__range=(today_start, today_end),
            status='Pending'
        ).select_related('patient')
        
        in_progress_consultancies = Consultancy.objects.filter(
            date_time__range=(today_start, today_end),
            status='Continue'
        ).select_related('patient')
        
        # Format the data for the WebSocket message
        pending_sessions_data = []
        for session in pending_sessions:
            pending_sessions_data.append({
                'id': session.id,
                'patient_name': session.patient.name,
                'phone_number': session.patient.phone_number,
                'time': session.date_time.strftime('%H:%M'),
                'gender': session.patient.gender,
                'type': 'Session'
            })
        
        in_progress_sessions_data = []
        for session in in_progress_sessions:
            in_progress_sessions_data.append({
                'id': session.id,
                'patient_name': session.patient.name,
                'phone_number': session.patient.phone_number,
                'time': session.date_time.strftime('%H:%M'),
                'gender': session.patient.gender,
                'type': 'Session'
            })
        
        pending_consultancies_data = []
        for consultancy in pending_consultancies:
            pending_consultancies_data.append({
                'id': consultancy.id,
                'patient_name': consultancy.patient.name,
                'phone_number': consultancy.patient.phone_number,
                'time': consultancy.date_time.strftime('%H:%M'),
                'gender': consultancy.patient.gender,
                'type': 'Consultancy'
            })
        
        in_progress_consultancies_data = []
        for consultancy in in_progress_consultancies:
            in_progress_consultancies_data.append({
                'id': consultancy.id,
                'patient_name': consultancy.patient.name,
                'phone_number': consultancy.patient.phone_number,
                'time': consultancy.date_time.strftime('%H:%M'),
                'gender': consultancy.patient.gender,
                'type': 'Consultancy'
            })

        message = {
            'type': 'send_patient_status',
            'message': f"A new session has been created with ID: {consultancy.id} for {consultancy.patient.name}",
            'pending_sessions': pending_sessions_data,
            'in_progress_sessions': in_progress_sessions_data,
            'pending_consultancies': pending_consultancies_data,
            'in_progress_consultancies': in_progress_consultancies_data
        }

        print(f"Sending message to group {group_name}: {message}")

        # Ensure you're using async_to_sync to call async method in a synchronous context
        async_to_sync(channel_layer.group_send)(
            group_name,
            message
        )