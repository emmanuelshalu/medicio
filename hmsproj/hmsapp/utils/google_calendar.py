from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from django.conf import settings
import json

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_google_calendar_service(credentials_json):
    """Create a Google Calendar service using stored credentials"""
    if not credentials_json:
        return None
    
    credentials = Credentials.from_authorized_user_info(
        json.loads(credentials_json), 
        SCOPES
    )
    
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            return None
            
    return build('calendar', 'v3', credentials=credentials)

def create_calendar_event(service, appointment):
    """Create a calendar event for an appointment"""
    if not service:
        return None
        
    event = {
        'summary': f'Appointment with {appointment.patient.full_name}',
        'description': f'Medical appointment\nPhone: {appointment.phone_number}\nNotes: {appointment.notes}',
        'start': {
            'dateTime': appointment.appointment_datetime.isoformat(),
            'timeZone': settings.TIME_ZONE,
        },
        'end': {
            'dateTime': (appointment.appointment_datetime + appointment.duration).isoformat(),
            'timeZone': settings.TIME_ZONE,
        },
        'reminders': {
            'useDefault': True
        },
    }
    
    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        return event.get('id')
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return None

def delete_calendar_event(service, event_id):
    """Delete a calendar event"""
    if not service or not event_id:
        return False
        
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting calendar event: {e}")
        return False