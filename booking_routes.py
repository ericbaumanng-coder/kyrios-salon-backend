"""
Booking System Routes for Kyrios Salon
- Services management
- Availability management
- Appointments booking with 20 CHF deposit
"""
from fastapi import APIRouter, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionResponse, CheckoutSessionRequest
)

logger = logging.getLogger(__name__)

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe API Key
stripe_api_key = os.environ.get('STRIPE_API_KEY', 'sk_test_emergent')

# Constants
DEPOSIT_AMOUNT = 20.0  # Fixed 20 CHF deposit for all appointments
BUFFER_MINUTES = 15  # Buffer between appointments
MIN_BOOKING_HOURS = 24  # Minimum 24h in advance
MAX_BOOKING_DAYS = 60  # Maximum 60 days in advance

# ============== MODELS ==============

class ServiceCategory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    name_de: Optional[str] = None
    description: Optional[str] = None
    order: int = 0


class Service(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category_id: str
    name: str
    name_de: Optional[str] = None
    price: float
    duration_minutes: int
    image_url: Optional[str] = None
    is_active: bool = True
    order: int = 0


class ServiceResponse(BaseModel):
    id: str
    category_id: str
    name: str
    name_de: Optional[str] = None
    price: float
    duration_minutes: int
    image_url: Optional[str] = None
    is_active: bool


class Availability(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str  # "07:30"
    end_time: str  # "18:30"
    is_active: bool = True


class TimeSlot(BaseModel):
    start_time: str
    end_time: str
    is_available: bool = True


class Appointment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    appointment_number: str
    service_id: str
    service_name: str
    service_price: float
    duration_minutes: int
    customer_name: str
    customer_email: str
    customer_phone: str
    appointment_date: str  # "2026-01-15"
    start_time: str  # "09:00"
    end_time: str  # "12:00"
    deposit_amount: float = DEPOSIT_AMOUNT
    deposit_paid: bool = False
    status: str = "pending"  # pending, confirmed, cancelled, completed, no_show
    stripe_session_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AppointmentCreate(BaseModel):
    service_id: str
    customer_name: str
    customer_email: str
    customer_phone: str
    appointment_date: str
    start_time: str
    notes: Optional[str] = None
    origin_url: str


class AppointmentResponse(BaseModel):
    id: str
    appointment_number: str
    service_id: str
    service_name: str
    service_price: float
    duration_minutes: int
    customer_name: str
    customer_email: str
    customer_phone: str
    appointment_date: str
    start_time: str
    end_time: str
    deposit_amount: float
    deposit_paid: bool
    status: str
    notes: Optional[str] = None
    created_at: str


# Create router
booking_router = APIRouter(prefix="/api")


# ============== HELPER FUNCTIONS ==============

def generate_appointment_number():
    now = datetime.now(timezone.utc)
    return f"RDV-{now.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"


def time_to_minutes(time_str: str) -> int:
    """Convert "HH:MM" to minutes since midnight"""
    hours, minutes = map(int, time_str.split(':'))
    return hours * 60 + minutes


def minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to "HH:MM"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def add_minutes_to_time(time_str: str, minutes: int) -> str:
    """Add minutes to a time string"""
    total_minutes = time_to_minutes(time_str) + minutes
    return minutes_to_time(total_minutes)


# ============== SERVICE CATEGORIES ROUTES ==============

@booking_router.get("/service-categories")
async def get_service_categories():
    categories = await db.service_categories.find({"is_active": {"$ne": False}}, {"_id": 0}).sort("order", 1).to_list(100)
    return categories


@booking_router.post("/admin/service-categories")
async def create_service_category(category: ServiceCategory):
    cat_dict = category.model_dump()
    await db.service_categories.insert_one(cat_dict)
    return {"id": category.id, "message": "Catégorie créée"}


# ============== SERVICES ROUTES ==============

@booking_router.get("/services")
async def get_services(category_id: Optional[str] = None, active_only: bool = True):
    query = {}
    if category_id:
        query["category_id"] = category_id
    if active_only:
        query["is_active"] = True
    
    services = await db.services.find(query, {"_id": 0}).sort("order", 1).to_list(100)
    return services


@booking_router.get("/services/{service_id}")
async def get_service(service_id: str):
    service = await db.services.find_one({"id": service_id}, {"_id": 0})
    if not service:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    return service


@booking_router.post("/admin/services")
async def create_service(service: Service):
    service_dict = service.model_dump()
    await db.services.insert_one(service_dict)
    return {"id": service.id, "message": "Service créé"}


@booking_router.put("/admin/services/{service_id}")
async def update_service(service_id: str, service: Service):
    result = await db.services.update_one(
        {"id": service_id},
        {"$set": service.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    return {"message": "Service mis à jour"}


# ============== AVAILABILITY ROUTES ==============

@booking_router.get("/availability")
async def get_availability():
    availability = await db.availability.find({"is_active": True}, {"_id": 0}).to_list(10)
    return availability


@booking_router.post("/admin/availability")
async def set_availability(availability_list: List[Availability]):
    # Clear existing and insert new
    await db.availability.delete_many({})
    for avail in availability_list:
        await db.availability.insert_one(avail.model_dump())
    return {"message": "Disponibilités mises à jour"}


@booking_router.get("/available-slots")
async def get_available_slots(date: str, service_id: str):
    """
    Get available time slots for a specific date and service.
    Takes into account service duration, existing appointments, and buffer time.
    """
    # Parse date
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide (YYYY-MM-DD)")
    
    # Check date constraints
    now = datetime.now(timezone.utc)
    min_date = now + timedelta(hours=MIN_BOOKING_HOURS)
    max_date = now + timedelta(days=MAX_BOOKING_DAYS)
    
    # Make target_date timezone aware for comparison
    target_datetime = target_date.replace(tzinfo=timezone.utc)
    
    if target_datetime.date() < min_date.date():
        return {"slots": [], "message": "La date doit être au moins 24h à l'avance"}
    
    if target_datetime.date() > max_date.date():
        return {"slots": [], "message": "La date ne peut pas dépasser 60 jours à l'avance"}
    
    # Get day of week (Python: Monday=0, Sunday=6)
    day_of_week = target_date.weekday()
    
    # Check if salon is open on this day (only Wed-Sat: 2,3,4,5)
    if day_of_week not in [2, 3, 4, 5]:  # Wednesday=2, Thursday=3, Friday=4, Saturday=5
        return {"slots": [], "message": "Le salon est fermé ce jour"}
    
    # Get availability for this day
    availability = await db.availability.find_one({"day_of_week": day_of_week, "is_active": True}, {"_id": 0})
    if not availability:
        return {"slots": [], "message": "Aucune disponibilité définie pour ce jour"}
    
    # Get service duration
    service = await db.services.find_one({"id": service_id}, {"_id": 0})
    if not service:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    
    service_duration = service["duration_minutes"]
    total_slot_duration = service_duration + BUFFER_MINUTES
    
    # Get existing appointments for this date
    existing_appointments = await db.appointments.find({
        "appointment_date": date,
        "status": {"$nin": ["cancelled"]}
    }, {"_id": 0}).to_list(100)
    
    # Generate time slots
    slots = []
    start_minutes = time_to_minutes(availability["start_time"])
    end_minutes = time_to_minutes(availability["end_time"])
    
    current_minutes = start_minutes
    
    while current_minutes + service_duration <= end_minutes:
        slot_start = minutes_to_time(current_minutes)
        slot_end = minutes_to_time(current_minutes + service_duration)
        
        # Check if slot conflicts with existing appointments
        is_available = True
        for appt in existing_appointments:
            appt_start = time_to_minutes(appt["start_time"])
            appt_end = time_to_minutes(appt["end_time"]) + BUFFER_MINUTES
            
            # Check for overlap
            if not (current_minutes + service_duration <= appt_start or current_minutes >= appt_end):
                is_available = False
                break
        
        # For today, check if slot is still in the future
        if target_date.date() == now.date():
            current_hour = now.hour
            current_min = now.minute
            if current_minutes < (current_hour * 60 + current_min + 60):  # At least 1h from now
                is_available = False
        
        if is_available:
            slots.append({
                "start_time": slot_start,
                "end_time": slot_end,
                "is_available": True
            })
        
        # Move to next slot (30 min intervals)
        current_minutes += 30
    
    return {"slots": slots, "date": date, "service_duration": service_duration}


# ============== APPOINTMENTS ROUTES ==============

@booking_router.get("/appointments")
async def get_appointments(date: Optional[str] = None, status: Optional[str] = None):
    query = {}
    if date:
        query["appointment_date"] = date
    if status:
        query["status"] = status
    
    appointments = await db.appointments.find(query, {"_id": 0}).sort("appointment_date", -1).to_list(1000)
    
    # Convert datetime objects to ISO strings
    for appt in appointments:
        if isinstance(appt.get('created_at'), datetime):
            appt['created_at'] = appt['created_at'].isoformat()
    
    return appointments


@booking_router.get("/appointments/{appointment_id}")
async def get_appointment(appointment_id: str):
    appointment = await db.appointments.find_one({"id": appointment_id}, {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    
    if isinstance(appointment.get('created_at'), datetime):
        appointment['created_at'] = appointment['created_at'].isoformat()
    
    return appointment


@booking_router.post("/appointments")
async def create_appointment(appointment_data: AppointmentCreate, request: Request):
    """Create a new appointment and initiate Stripe checkout for deposit"""
    
    # Get service
    service = await db.services.find_one({"id": appointment_data.service_id}, {"_id": 0})
    if not service:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    
    # Validate date and time
    try:
        target_date = datetime.strptime(appointment_data.appointment_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide")
    
    # Check availability
    day_of_week = target_date.weekday()
    if day_of_week not in [2, 3, 4, 5]:
        raise HTTPException(status_code=400, detail="Le salon est fermé ce jour")
    
    # Calculate end time
    start_minutes = time_to_minutes(appointment_data.start_time)
    end_time = minutes_to_time(start_minutes + service["duration_minutes"])
    
    # Check for conflicts
    existing = await db.appointments.find_one({
        "appointment_date": appointment_data.appointment_date,
        "status": {"$nin": ["cancelled"]},
        "$or": [
            {
                "start_time": {"$lt": end_time},
                "end_time": {"$gt": appointment_data.start_time}
            }
        ]
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Ce créneau n'est plus disponible")
    
    # Create appointment
    appointment = Appointment(
        appointment_number=generate_appointment_number(),
        service_id=service["id"],
        service_name=service["name"],
        service_price=service["price"],
        duration_minutes=service["duration_minutes"],
        customer_name=appointment_data.customer_name,
        customer_email=appointment_data.customer_email,
        customer_phone=appointment_data.customer_phone,
        appointment_date=appointment_data.appointment_date,
        start_time=appointment_data.start_time,
        end_time=end_time,
        notes=appointment_data.notes
    )
    
    appt_dict = appointment.model_dump()
    appt_dict['created_at'] = appt_dict['created_at'].isoformat()
    await db.appointments.insert_one(appt_dict)
    
    # Create Stripe checkout session for deposit
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    origin_url = appointment_data.origin_url.rstrip('/')
    success_url = f"{origin_url}/booking-confirmation?appointment_id={appointment.id}"
    cancel_url = f"{origin_url}?booking_cancelled=true"
    
    metadata = {
        "appointment_id": appointment.id,
        "appointment_number": appointment.appointment_number,
        "customer_email": appointment_data.customer_email,
        "type": "booking_deposit"
    }
    
    checkout_request = CheckoutSessionRequest(
        amount=DEPOSIT_AMOUNT,
        currency="chf",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata
    )
    
    try:
        checkout_session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Update appointment with stripe session
        await db.appointments.update_one(
            {"id": appointment.id},
            {"$set": {"stripe_session_id": checkout_session.session_id}}
        )
        
        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.session_id,
            "appointment_id": appointment.id,
            "appointment_number": appointment.appointment_number,
            "deposit_amount": DEPOSIT_AMOUNT
        }
        
    except Exception as e:
        logger.error(f"Stripe checkout error for booking: {e}")
        # Delete the appointment if payment fails
        await db.appointments.delete_one({"id": appointment.id})
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du paiement: {str(e)}")


@booking_router.get("/appointments/by-session/{session_id}")
async def get_appointment_by_stripe_session(session_id: str):
    appointment = await db.appointments.find_one({"stripe_session_id": session_id}, {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    
    if isinstance(appointment.get('created_at'), datetime):
        appointment['created_at'] = appointment['created_at'].isoformat()
    
    return appointment


# ============== ADMIN APPOINTMENT ROUTES ==============

@booking_router.get("/admin/appointments")
async def get_all_appointments(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None
):
    query = {}
    
    if start_date and end_date:
        query["appointment_date"] = {"$gte": start_date, "$lte": end_date}
    elif start_date:
        query["appointment_date"] = {"$gte": start_date}
    elif end_date:
        query["appointment_date"] = {"$lte": end_date}
    
    if status:
        query["status"] = status
    
    appointments = await db.appointments.find(query, {"_id": 0}).sort([
        ("appointment_date", 1),
        ("start_time", 1)
    ]).to_list(1000)
    
    for appt in appointments:
        if isinstance(appt.get('created_at'), datetime):
            appt['created_at'] = appt['created_at'].isoformat()
    
    return appointments


class AppointmentStatusUpdate(BaseModel):
    status: str


@booking_router.patch("/admin/appointments/{appointment_id}/status")
async def update_appointment_status(appointment_id: str, status_update: AppointmentStatusUpdate):
    valid_statuses = ["pending", "confirmed", "cancelled", "completed", "no_show"]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Statut invalide")
    
    result = await db.appointments.update_one(
        {"id": appointment_id},
        {"$set": {"status": status_update.status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    
    return {"message": "Statut mis à jour", "status": status_update.status}


@booking_router.delete("/admin/appointments/{appointment_id}")
async def cancel_appointment(appointment_id: str):
    result = await db.appointments.update_one(
        {"id": appointment_id},
        {"$set": {"status": "cancelled"}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    
    return {"message": "Rendez-vous annulé"}


# ============== BOOKING STATS ==============

@booking_router.get("/admin/booking-stats")
async def get_booking_stats():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    
    # Get appointments
    all_appointments = await db.appointments.find({}, {"_id": 0}).to_list(1000)
    
    # Calculate stats
    today_appointments = sum(1 for a in all_appointments if a["appointment_date"] == today and a["status"] != "cancelled")
    week_appointments = sum(1 for a in all_appointments if a["appointment_date"] >= week_start and a["status"] != "cancelled")
    pending_confirmations = sum(1 for a in all_appointments if a["status"] == "pending")
    
    # Total deposits received this month
    deposits_received = sum(
        a.get("deposit_amount", 0)
        for a in all_appointments
        if a.get("deposit_paid") and a["appointment_date"] >= month_start
    )
    
    # Upcoming appointments (next 7 days)
    next_week = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    upcoming = [
        a for a in all_appointments
        if a["appointment_date"] >= today and a["appointment_date"] <= next_week and a["status"] not in ["cancelled", "completed"]
    ]
    upcoming.sort(key=lambda x: (x["appointment_date"], x["start_time"]))
    
    return {
        "today_appointments": today_appointments,
        "week_appointments": week_appointments,
        "pending_confirmations": pending_confirmations,
        "deposits_received": deposits_received,
        "upcoming_appointments": upcoming[:10]  # Next 10 appointments
    }
