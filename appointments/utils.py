from datetime import datetime, time

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from .models import Consultancy, Session, RecordLog


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
        date_time__range=(today_start, today_end), status="Pending"
    ).select_related("patient")

    in_progress_sessions = Session.objects.filter(
        date_time__range=(today_start, today_end), status="Continue"
    ).select_related("patient")

    # Get pending and continue consultancies for today
    pending_consultancies = Consultancy.objects.filter(
        date_time__range=(today_start, today_end), status="Pending"
    ).select_related("patient")

    in_progress_consultancies = Consultancy.objects.filter(
        date_time__range=(today_start, today_end), status="Continue"
    ).select_related("patient")

    # Format the data for the WebSocket message
    pending_sessions_data = []
    for session in pending_sessions:
        pending_sessions_data.append(
            {
                "id": session.id,
                "patient_name": session.patient.name,
                "phone_number": session.patient.phone_number,
                "time": session.date_time.strftime("%H:%M"),
                "gender": session.patient.gender,
                "type": "Session",
            }
        )

    in_progress_sessions_data = []
    for session in in_progress_sessions:
        in_progress_sessions_data.append(
            {
                "id": session.id,
                "patient_name": session.patient.name,
                "phone_number": session.patient.phone_number,
                "time": session.date_time.strftime("%H:%M"),
                "gender": session.patient.gender,
                "type": "Session",
            }
        )

    pending_consultancies_data = []
    for consultancy in pending_consultancies:
        pending_consultancies_data.append(
            {
                "id": consultancy.id,
                "patient_name": consultancy.patient.name,
                "phone_number": consultancy.patient.phone_number,
                "time": consultancy.date_time.strftime("%H:%M"),
                "gender": consultancy.patient.gender,
                "type": "Consultancy",
            }
        )

    in_progress_consultancies_data = []
    for consultancy in in_progress_consultancies:
        in_progress_consultancies_data.append(
            {
                "id": consultancy.id,
                "patient_name": consultancy.patient.name,
                "phone_number": consultancy.patient.phone_number,
                "time": consultancy.date_time.strftime("%H:%M"),
                "gender": consultancy.patient.gender,
                "type": "Consultancy",
            }
        )

    message = {
        "type": "send_patient_status",
        "message": f"A new session has been created with ID: {consultancy.id} for {consultancy.patient.name}",
        "pending_sessions": pending_sessions_data,
        "in_progress_sessions": in_progress_sessions_data,
        "pending_consultancies": pending_consultancies_data,
        "in_progress_consultancies": in_progress_consultancies_data,
    }

    # Ensure you're using async_to_sync to call async method in a synchronous context
    async_to_sync(channel_layer.group_send)(group_name, message)


def categorize_feedback(feedback_text):
    """Categorize feedback as positive, negative, mixed, or neutral"""
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


def create_consultancy_record_log(consultancy):
    """Create a RecordLog entry for a consultancy"""
    # Calculate net amount (consultancy fee - discount)
    net_amount = float(consultancy.consultancy_fee)

    # Get doctor name
    doctor_name = (
        consultancy.referred_doctor.username if consultancy.referred_doctor else "N/A"
    )

    # Create the record log
    record_log = RecordLog.objects.create(
        record_type="consultancy",
        date_time=consultancy.date_time,
        patient=consultancy.patient,
        patient_name=consultancy.patient.name,
        patient_phone=consultancy.patient.phone_number,
        patient_gender=consultancy.patient.gender,
        doctor=consultancy.referred_doctor,
        doctor_name=doctor_name,
        amount=consultancy.consultancy_fee,
        discount=consultancy.discount or 0,
        further_discount=0,  # Consultancies don't have further discount
        net_amount=net_amount,
        status=consultancy.status,
        feedback=consultancy.chief_complaint,
        feedback_type=categorize_feedback(consultancy.chief_complaint),
        consultancy=consultancy,
        organization=consultancy.patient.organization,
        number_of_sessions=consultancy.number_of_sessions,
        chief_complaint=consultancy.chief_complaint,
    )

    return record_log


def create_session_record_log(session):
    """Create a RecordLog entry for a session"""
    # Get the related consultancy for discount calculation
    related_consultancy = session.consultancy
    consultancy_discount = (
        related_consultancy.discount
        if related_consultancy and related_consultancy.discount
        else 0
    )

    # Calculate net amount (session fee - consultancy discount)
    net_amount = float(session.session_fee) - float(consultancy_discount)

    # Get doctor name
    doctor_name = session.doctor.username if session.doctor else "N/A"

    # Create the record log
    record_log = RecordLog.objects.create(
        record_type="session",
        date_time=session.date_time,
        patient=session.patient,
        patient_name=session.patient.name,
        patient_phone=session.patient.phone_number,
        patient_gender=session.patient.gender,
        doctor=session.doctor,
        doctor_name=doctor_name,
        amount=session.session_fee,
        discount=consultancy_discount,  # Discount from consultancy
        further_discount=session.further_discount or 0,
        net_amount=net_amount,
        status=session.status,
        feedback=session.feedback,
        feedback_type=categorize_feedback(session.feedback),
        session=session,
        consultancy=related_consultancy,
        organization=session.patient.organization,
    )

    return record_log


def update_consultancy_record_log(consultancy):
    """Update existing RecordLog entry for a consultancy"""
    try:
        record_log = RecordLog.objects.get(consultancy=consultancy)

        # Recalculate values
        net_amount = float(consultancy.consultancy_fee)
        doctor_name = (
            consultancy.referred_doctor.username
            if consultancy.referred_doctor
            else "N/A"
        )

        # Update the record log
        record_log.patient_name = consultancy.patient.name
        record_log.patient_phone = consultancy.patient.phone_number
        record_log.patient_gender = consultancy.patient.gender
        record_log.doctor = consultancy.referred_doctor
        record_log.doctor_name = doctor_name
        record_log.amount = consultancy.consultancy_fee
        record_log.discount = consultancy.discount or 0
        record_log.net_amount = net_amount
        record_log.status = consultancy.status
        record_log.feedback = consultancy.chief_complaint
        record_log.feedback_type = categorize_feedback(consultancy.chief_complaint)
        record_log.number_of_sessions = consultancy.number_of_sessions
        record_log.chief_complaint = consultancy.chief_complaint
        record_log.save()

        return record_log
    except RecordLog.DoesNotExist:
        # If record doesn't exist, create it
        return create_consultancy_record_log(consultancy)


def update_session_record_log(session):
    """Update existing RecordLog entry for a session"""
    try:
        record_log = RecordLog.objects.get(session=session)

        # Recalculate values
        related_consultancy = session.consultancy
        consultancy_discount = (
            related_consultancy.discount
            if related_consultancy and related_consultancy.discount
            else 0
        )
        net_amount = float(session.session_fee) - float(consultancy_discount)
        doctor_name = session.doctor.username if session.doctor else "N/A"

        # Update the record log
        record_log.patient_name = session.patient.name
        record_log.patient_phone = session.patient.phone_number
        record_log.patient_gender = session.patient.gender
        record_log.doctor = session.doctor
        record_log.doctor_name = doctor_name
        record_log.amount = session.session_fee
        record_log.discount = consultancy_discount
        record_log.further_discount = session.further_discount or 0
        record_log.net_amount = net_amount
        record_log.status = session.status
        record_log.feedback = session.feedback
        record_log.feedback_type = categorize_feedback(session.feedback)
        record_log.save()

        return record_log
    except RecordLog.DoesNotExist:
        # If record doesn't exist, create it
        return create_session_record_log(session)


def delete_record_log(record_type, related_id):
    """Delete RecordLog entry for a consultancy or session"""
    try:
        if record_type == "consultancy":
            record_log = RecordLog.objects.get(consultancy_id=related_id)
        elif record_type == "session":
            record_log = RecordLog.objects.get(session_id=related_id)
        else:
            return False

        record_log.delete()
        return True
    except RecordLog.DoesNotExist:
        return False


def send_session_creation_notification(session):
    """Send notification when a session is created"""
    # This function can be implemented later for notifications
    pass
