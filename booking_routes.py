"""
Booking System Routes for Kyrios Salon
- Services management with size variations
- Availability management
- Appointments booking with 20 CHF deposit
"""
from fastapi import APIRouter, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta
import uuid
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import stripe

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
stripe.api_key = stripe_api_key

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
    icon: Optional[str] = None
    image_url: Optional[str] = None
    order: int = 0
    is_active: bool = True


class SizeVariation(BaseModel):
    size: str  # XS, S, M, L, XL or custom
    price: float
    duration_minutes: int


class ThicknessVariation(BaseModel):
    """Thickness/width variation for braids (Tresses category only)"""
    thickness: str  # Très Fin, Fin, Moyen, Large, Très Large
    price_modifier: float  # Additional price to add
    duration_modifier: int  # Additional minutes to add


class ServiceModel(BaseModel):
    """A service model with size variations (e.g., Box Braids with S/M/L)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category_id: str
    name: str
    name_de: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    variations: List[SizeVariation] = []
    thickness_variations: Optional[List[ThicknessVariation]] = None  # Only for Tresses category
    has_thickness: bool = False  # Flag to indicate if this service uses thickness pricing
    is_active: bool = True
    order: int = 0


class Service(BaseModel):
    """Legacy service model for backwards compatibility"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category_id: str
    name: str
    name_de: Optional[str] = None
    price: float
    duration_minutes: int
    description: Optional[str] = None
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
    # New model - with service model and variation
    service_model_id: Optional[str] = None
    service_name: Optional[str] = None
    variation_size: Optional[str] = None
    price: Optional[float] = None
    duration_minutes: Optional[int] = None
    # Legacy field for backward compatibility
    service_id: Optional[str] = None
    # Customer info
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
async def get_available_slots(date: str, duration: Optional[int] = None, service_id: Optional[str] = None):
    """
    Get available time slots for a specific date.
    SMART BOOKING LOGIC:
    1. First booking of the day MUST start at opening time
    2. Subsequent bookings start immediately after the previous one ends
    3. Slots that would extend past closing time are not offered
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
    
    # Check for blocked dates
    blocked = await db.blocked_dates.find_one({"date": date})
    if blocked:
        return {"slots": [], "message": blocked.get("reason", "Date bloquée")}
    
    # Get availability for this day
    availability = await db.availability.find_one({"day_of_week": day_of_week, "is_active": True}, {"_id": 0})
    if not availability:
        return {"slots": [], "message": "Le salon est fermé ce jour"}
    
    # Get service duration - from duration parameter or service_id for backward compatibility
    service_duration = duration
    if not service_duration and service_id:
        service = await db.services.find_one({"id": service_id}, {"_id": 0})
        if service:
            service_duration = service["duration_minutes"]
    
    if not service_duration:
        service_duration = 60  # Default 1 hour if nothing specified
    
    # Get salon opening and closing times
    opening_minutes = time_to_minutes(availability["start_time"])
    closing_minutes = time_to_minutes(availability["end_time"])
    
    # Check if service can fit within the day at all
    if service_duration > (closing_minutes - opening_minutes):
        return {"slots": [], "message": f"Cette prestation ({service_duration} min) est trop longue pour ce jour"}
    
    # Get existing appointments for this date, sorted by start time
    existing_appointments = await db.appointments.find({
        "appointment_date": date,
        "status": {"$nin": ["cancelled"]}
    }, {"_id": 0}).sort("start_time", 1).to_list(100)
    
    # SMART SLOT LOGIC
    slots = []
    
    if len(existing_appointments) == 0:
        # NO APPOINTMENTS YET: First booking MUST be at opening time
        slot_start = minutes_to_time(opening_minutes)
        slot_end = minutes_to_time(opening_minutes + service_duration)
        
        # For today, check if opening time is still in the future
        is_available = True
        if target_date.date() == now.date():
            current_total_min = now.hour * 60 + now.minute + 60  # At least 1h from now
            if opening_minutes < current_total_min:
                is_available = False
        
        if is_available:
            slots.append({
                "start_time": slot_start,
                "end_time": slot_end,
                "is_available": True,
                "slot_info": "Premier créneau de la journée"
            })
    else:
        # APPOINTMENTS EXIST: Find slots that start immediately after existing appointments
        
        # First, check if there's a slot at opening (before first appointment)
        first_appt_start = time_to_minutes(existing_appointments[0]["start_time"])
        if first_appt_start > opening_minutes:
            # There's a gap at the beginning - offer opening slot if duration fits
            if (first_appt_start - opening_minutes) >= service_duration:
                slot_start = minutes_to_time(opening_minutes)
                slot_end = minutes_to_time(opening_minutes + service_duration)
                
                is_available = True
                if target_date.date() == now.date():
                    current_total_min = now.hour * 60 + now.minute + 60
                    if opening_minutes < current_total_min:
                        is_available = False
                
                if is_available:
                    slots.append({
                        "start_time": slot_start,
                        "end_time": slot_end,
                        "is_available": True,
                        "slot_info": "Créneau d'ouverture"
                    })
        
        # Then, check slots after each existing appointment
        for i, appt in enumerate(existing_appointments):
            appt_end_minutes = time_to_minutes(appt["end_time"])
            
            # Determine the next constraint (next appointment start or closing time)
            if i + 1 < len(existing_appointments):
                next_constraint = time_to_minutes(existing_appointments[i + 1]["start_time"])
            else:
                next_constraint = closing_minutes
            
            # Calculate available gap
            available_gap = next_constraint - appt_end_minutes
            
            # If service fits in the gap, offer the slot
            if available_gap >= service_duration:
                slot_start_minutes = appt_end_minutes
                slot_start = minutes_to_time(slot_start_minutes)
                slot_end = minutes_to_time(slot_start_minutes + service_duration)
                
                # For today, check if slot is still in the future
                is_available = True
                if target_date.date() == now.date():
                    current_total_min = now.hour * 60 + now.minute + 60
                    if slot_start_minutes < current_total_min:
                        is_available = False
                
                if is_available:
                    slots.append({
                        "start_time": slot_start,
                        "end_time": slot_end,
                        "is_available": True,
                        "slot_info": f"Suite au RDV de {appt.get('customer_name', 'client').split()[0]}"
                    })
    
    # If no slots are available
    if len(slots) == 0:
        # Check if there's time remaining after all appointments
        if existing_appointments:
            last_appt = existing_appointments[-1]
            last_end = time_to_minutes(last_appt["end_time"])
            remaining_time = closing_minutes - last_end
            
            if remaining_time > 0 and remaining_time < service_duration:
                return {
                    "slots": [], 
                    "message": f"Il reste {remaining_time} min après le dernier RDV, insuffisant pour cette prestation ({service_duration} min)",
                    "suggestion": "Essayez un autre jour ou une prestation plus courte"
                }
        
        return {"slots": [], "message": "Aucun créneau disponible pour cette date"}
    
    return {
        "slots": slots, 
        "date": date, 
        "service_duration": service_duration,
        "salon_hours": f"{availability['start_time']} - {availability['end_time']}",
        "smart_booking": True
    }


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
    
    # Determine service info - new format with service_model_id or legacy with service_id
    service_name = None
    service_price = None
    service_duration = None
    service_id = None
    variation_size = None
    
    if appointment_data.service_model_id and appointment_data.price and appointment_data.duration_minutes:
        # New format - use provided data directly from variation
        service_name = appointment_data.service_name
        service_price = appointment_data.price
        service_duration = appointment_data.duration_minutes
        service_id = appointment_data.service_model_id
        variation_size = appointment_data.variation_size
    elif appointment_data.service_id:
        # Legacy format - lookup service from DB
        service = await db.services.find_one({"id": appointment_data.service_id}, {"_id": 0})
        if not service:
            raise HTTPException(status_code=404, detail="Service non trouvé")
        service_name = service["name"]
        service_price = service["price"]
        service_duration = service["duration_minutes"]
        service_id = service["id"]
    else:
        raise HTTPException(status_code=400, detail="Service model ou service_id requis")
    
    # Validate date and time
    try:
        target_date = datetime.strptime(appointment_data.appointment_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide")
    
    # Check availability
    day_of_week = target_date.weekday()
    if day_of_week not in [2, 3, 4, 5]:
        raise HTTPException(status_code=400, detail="Le salon est fermé ce jour")
    
    # Check for blocked dates
    blocked = await db.blocked_dates.find_one({"date": appointment_data.appointment_date})
    if blocked:
        raise HTTPException(status_code=400, detail=blocked.get("reason", "Date bloquée"))
    
    # Calculate end time
    start_minutes = time_to_minutes(appointment_data.start_time)
    end_time = minutes_to_time(start_minutes + service_duration)
    
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
        service_id=service_id,
        service_name=service_name + (f" ({variation_size})" if variation_size and variation_size != "Unique" else ""),
        service_price=service_price,
        duration_minutes=service_duration,
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
    origin_url = appointment_data.origin_url.rstrip('/')
    success_url = f"{origin_url}/booking-confirmation?appointment_id={appointment.id}"
    cancel_url = f"{origin_url}?booking_cancelled=true"
    
    metadata = {
        "appointment_id": appointment.id,
        "appointment_number": appointment.appointment_number,
        "customer_email": appointment_data.customer_email,
        "type": "booking_deposit"
    }
    
    try:
        # Create Stripe checkout session using standard stripe library
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "chf",
                    "product_data": {
                        "name": f"Acompte RDV - {service_name}" + (f" ({variation_size})" if variation_size and variation_size != "Unique" else ""),
                        "description": f"Réservation {appointment.appointment_number}"
                    },
                    "unit_amount": int(DEPOSIT_AMOUNT * 100),  # Stripe uses cents
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            customer_email=appointment_data.customer_email,
        )
        
        # Update appointment with stripe session
        await db.appointments.update_one(
            {"id": appointment.id},
            {"$set": {"stripe_session_id": checkout_session.id}}
        )
        
        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id,
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


# ============== SEED/INIT SERVICES ==============

@booking_router.post("/admin/init-services-v2")
async def init_services_v2():
    """Initialize the database with service models that have size variations"""
    
    # Service Categories
    CATEGORIES = [
        {
            "id": "cat_tresses",
            "name": "Tresses & Coiffures Naturelles",
            "name_de": "Zöpfe & Natürliche Frisuren",
            "description": "Box braids, knotless, twists et plus",
            "icon": "scissors",
            "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=400",
            "order": 1,
            "is_active": True
        },
        {
            "id": "cat_tissage",
            "name": "Tissage & Pose",
            "name_de": "Einnähen & Perückenanbringung",
            "description": "Tissage, closure, frontale et ponytail",
            "icon": "sparkles",
            "image_url": "https://images.unsplash.com/photo-1595499280852-21f4f3a64400?w=400",
            "order": 2,
            "is_active": True
        },
        {
            "id": "cat_locks",
            "name": "Locks",
            "name_de": "Dreadlocks",
            "description": "Création et entretien de locks",
            "icon": "crown",
            "image_url": "https://images.unsplash.com/photo-1611175603085-e7ceaf1f8a9f?w=400",
            "order": 3,
            "is_active": True
        },
        {
            "id": "cat_soins",
            "name": "Soins & Styling",
            "name_de": "Pflege & Styling",
            "description": "Soins, brushing, lissage et coupe",
            "icon": "heart",
            "image_url": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=400",
            "order": 4,
            "is_active": True
        }
    ]

    # Service Models with size variations
    SERVICE_MODELS = [
        # FAMILLE 1 — Tresses & Coiffures Naturelles
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_tresses",
            "name": "Box Braids",
            "description": "Petites tresses classiques",
            "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=400",
            "variations": [
                {"size": "S", "price": 80, "duration_minutes": 180},
                {"size": "M", "price": 120, "duration_minutes": 240},
                {"size": "L", "price": 160, "duration_minutes": 300}
            ],
            "is_active": True,
            "order": 1
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_tresses",
            "name": "Knotless Braids",
            "description": "Tresses sans nœud, plus légères et naturelles",
            "image_url": "https://images.unsplash.com/photo-1595499280852-21f4f3a64400?w=400",
            "variations": [
                {"size": "S", "price": 100, "duration_minutes": 210},
                {"size": "M", "price": 140, "duration_minutes": 270},
                {"size": "L", "price": 180, "duration_minutes": 330}
            ],
            "is_active": True,
            "order": 2
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_tresses",
            "name": "Senegalese Twists",
            "description": "Vanilles sénégalaises élégantes",
            "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=400",
            "variations": [
                {"size": "S", "price": 80, "duration_minutes": 180},
                {"size": "M", "price": 120, "duration_minutes": 240},
                {"size": "L", "price": 160, "duration_minutes": 300}
            ],
            "is_active": True,
            "order": 3
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_tresses",
            "name": "Goddess Braids",
            "description": "Tresses déesse bohème avec mèches ondulées",
            "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=400",
            "variations": [
                {"size": "S", "price": 90, "duration_minutes": 180},
                {"size": "M", "price": 130, "duration_minutes": 240},
                {"size": "L", "price": 170, "duration_minutes": 300}
            ],
            "is_active": True,
            "order": 4
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_tresses",
            "name": "Ghana Braids",
            "description": "Tresses collées Ghana traditionnelles",
            "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=400",
            "variations": [
                {"size": "S", "price": 70, "duration_minutes": 150},
                {"size": "L", "price": 130, "duration_minutes": 240}
            ],
            "is_active": True,
            "order": 5
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_tresses",
            "name": "Cornrows Simple",
            "description": "Nattes collées simples et épurées",
            "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=400",
            "variations": [
                {"size": "Unique", "price": 40, "duration_minutes": 60}
            ],
            "is_active": True,
            "order": 6
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_tresses",
            "name": "Cornrows Complexes",
            "description": "Nattes collées avec motifs élaborés",
            "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=400",
            "variations": [
                {"size": "Unique", "price": 90, "duration_minutes": 150}
            ],
            "is_active": True,
            "order": 7
        },
        
        # FAMILLE 2 — Tissage & Pose
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_tissage",
            "name": "Tissage",
            "description": "Tissage classique cousu",
            "image_url": "https://images.unsplash.com/photo-1595499280852-21f4f3a64400?w=400",
            "variations": [
                {"size": "Unique", "price": 80, "duration_minutes": 90}
            ],
            "is_active": True,
            "order": 1
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_tissage",
            "name": "Pose Closure",
            "description": "Pose de closure pour un look naturel",
            "image_url": "https://images.unsplash.com/photo-1595499280852-21f4f3a64400?w=400",
            "variations": [
                {"size": "Unique", "price": 60, "duration_minutes": 90}
            ],
            "is_active": True,
            "order": 2
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_tissage",
            "name": "Pose Frontale",
            "description": "Pose de frontale lace pour effet baby hair",
            "image_url": "https://images.unsplash.com/photo-1595499280852-21f4f3a64400?w=400",
            "variations": [
                {"size": "Unique", "price": 80, "duration_minutes": 120}
            ],
            "is_active": True,
            "order": 3
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_tissage",
            "name": "Pose Ponytail",
            "description": "Pose de queue de cheval élégante",
            "image_url": "https://images.unsplash.com/photo-1595499280852-21f4f3a64400?w=400",
            "variations": [
                {"size": "Unique", "price": 50, "duration_minutes": 60}
            ],
            "is_active": True,
            "order": 4
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_tissage",
            "name": "360 Frontale / Full Lace",
            "description": "Pose complète 360 ou full lace premium",
            "image_url": "https://images.unsplash.com/photo-1595499280852-21f4f3a64400?w=400",
            "variations": [
                {"size": "Unique", "price": 120, "duration_minutes": 150}
            ],
            "is_active": True,
            "order": 5
        },
        
        # FAMILLE 3 — Locks
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_locks",
            "name": "Locks Start",
            "description": "Création de locks - Démarrage de votre voyage",
            "image_url": "https://images.unsplash.com/photo-1611175603085-e7ceaf1f8a9f?w=400",
            "variations": [
                {"size": "Unique", "price": 150, "duration_minutes": 180}
            ],
            "is_active": True,
            "order": 1
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_locks",
            "name": "Locks Maintenance",
            "description": "Entretien régulier de vos locks",
            "image_url": "https://images.unsplash.com/photo-1611175603085-e7ceaf1f8a9f?w=400",
            "variations": [
                {"size": "Unique", "price": 60, "duration_minutes": 90}
            ],
            "is_active": True,
            "order": 2
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_locks",
            "name": "Locks Retouch",
            "description": "Retouche racines des locks",
            "image_url": "https://images.unsplash.com/photo-1611175603085-e7ceaf1f8a9f?w=400",
            "variations": [
                {"size": "Unique", "price": 40, "duration_minutes": 60}
            ],
            "is_active": True,
            "order": 3
        },
        
        # FAMILLE 4 — Soins & Styling
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_soins",
            "name": "Soin Deep Treatment",
            "description": "Soin profond hydratant et réparateur",
            "image_url": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=400",
            "variations": [
                {"size": "Unique", "price": 50, "duration_minutes": 60}
            ],
            "is_active": True,
            "order": 1
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_soins",
            "name": "Brushing",
            "description": "Brushing lisse ou wavy professionnel",
            "image_url": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=400",
            "variations": [
                {"size": "Unique", "price": 30, "duration_minutes": 45}
            ],
            "is_active": True,
            "order": 2
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_soins",
            "name": "Dégradé",
            "description": "Coupe dégradée tendance",
            "image_url": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=400",
            "variations": [
                {"size": "Unique", "price": 35, "duration_minutes": 45}
            ],
            "is_active": True,
            "order": 3
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_soins",
            "name": "Lissage Kératine",
            "description": "Lissage brésilien à la kératine longue durée",
            "image_url": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=400",
            "variations": [
                {"size": "Unique", "price": 120, "duration_minutes": 120}
            ],
            "is_active": True,
            "order": 4
        },
        {
            "id": str(uuid.uuid4()),
            "category_id": "cat_soins",
            "name": "Coupe + Soin",
            "description": "Coupe personnalisée avec soin inclus",
            "image_url": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=400",
            "variations": [
                {"size": "Unique", "price": 45, "duration_minutes": 60}
            ],
            "is_active": True,
            "order": 5
        }
    ]

    # Default availability (Wednesday to Saturday, 7:30 - 18:30)
    AVAILABILITY = [
        {"id": str(uuid.uuid4()), "day_of_week": 2, "day_name": "Mercredi", "start_time": "07:30", "end_time": "18:30", "is_active": True},
        {"id": str(uuid.uuid4()), "day_of_week": 3, "day_name": "Jeudi", "start_time": "07:30", "end_time": "18:30", "is_active": True},
        {"id": str(uuid.uuid4()), "day_of_week": 4, "day_name": "Vendredi", "start_time": "07:30", "end_time": "18:30", "is_active": True},
        {"id": str(uuid.uuid4()), "day_of_week": 5, "day_name": "Samedi", "start_time": "07:30", "end_time": "18:30", "is_active": True},
    ]
    
    try:
        # Clear existing data
        await db.service_categories.delete_many({})
        await db.service_models.delete_many({})
        await db.availability.delete_many({})
        await db.blocked_dates.delete_many({})
        
        # Insert categories
        await db.service_categories.insert_many(CATEGORIES)
        
        # Insert service models
        await db.service_models.insert_many(SERVICE_MODELS)
        
        # Insert availability
        await db.availability.insert_many(AVAILABILITY)
        
        return {
            "success": True,
            "message": "Services V2 initialisés avec succès",
            "categories_count": len(CATEGORIES),
            "service_models_count": len(SERVICE_MODELS),
            "availability_count": len(AVAILABILITY)
        }
    except Exception as e:
        logger.error(f"Error initializing services V2: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


# Keep the old init for backwards compatibility
@booking_router.post("/admin/init-services")
async def init_services():
    return await init_services_v2()


# ============== SERVICE MODELS MANAGEMENT ==============

@booking_router.get("/service-models")
async def get_service_models():
    """Get all service models with variations"""
    models = await db.service_models.find({"is_active": True}, {"_id": 0}).to_list(100)
    return models


@booking_router.get("/service-models/by-category/{category_id}")
async def get_service_models_by_category(category_id: str):
    """Get service models for a specific category"""
    models = await db.service_models.find(
        {"category_id": category_id, "is_active": True}, 
        {"_id": 0}
    ).sort("order", 1).to_list(100)
    return models


@booking_router.get("/admin/service-models")
async def get_all_service_models_admin():
    """Admin: Get all service models including inactive"""
    models = await db.service_models.find({}, {"_id": 0}).to_list(100)
    return models


@booking_router.post("/admin/service-models")
async def create_service_model(model: ServiceModel):
    """Admin: Create a new service model"""
    model_dict = model.model_dump()
    await db.service_models.insert_one(model_dict)
    return {"message": "Modèle de service créé", "id": model.id}


@booking_router.put("/admin/service-models/{model_id}")
async def update_service_model(model_id: str, model: ServiceModel):
    """Admin: Update a service model"""
    model_dict = model.model_dump()
    model_dict["id"] = model_id
    
    result = await db.service_models.update_one(
        {"id": model_id},
        {"$set": model_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Modèle non trouvé")
    
    return {"message": "Modèle mis à jour"}


@booking_router.delete("/admin/service-models/{model_id}")
async def delete_service_model(model_id: str):
    """Admin: Delete a service model"""
    result = await db.service_models.delete_one({"id": model_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Modèle non trouvé")
    
    return {"message": "Modèle supprimé"}


# ============== CATEGORY MANAGEMENT ==============

@booking_router.post("/admin/service-categories")
async def create_category(category: ServiceCategory):
    """Admin: Create a new category"""
    cat_dict = category.model_dump()
    await db.service_categories.insert_one(cat_dict)
    return {"message": "Catégorie créée", "id": category.id}


@booking_router.put("/admin/service-categories/{category_id}")
async def update_category(category_id: str, category: ServiceCategory):
    """Admin: Update a category"""
    cat_dict = category.model_dump()
    cat_dict["id"] = category_id
    
    result = await db.service_categories.update_one(
        {"id": category_id},
        {"$set": cat_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Catégorie non trouvée")
    
    return {"message": "Catégorie mise à jour"}


@booking_router.delete("/admin/service-categories/{category_id}")
async def delete_category(category_id: str):
    """Admin: Delete a category"""
    # Check if any services use this category
    services_count = await db.service_models.count_documents({"category_id": category_id})
    if services_count > 0:
        raise HTTPException(status_code=400, detail=f"Impossible de supprimer: {services_count} services utilisent cette catégorie")
    
    result = await db.service_categories.delete_one({"id": category_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Catégorie non trouvée")
    
    return {"message": "Catégorie supprimée"}


# ============== THICKNESS PRICING FOR TRESSES ==============

# Default thickness variations for braids (now using size codes)
DEFAULT_THICKNESS_VARIATIONS = [
    {"thickness": "XS", "price_modifier": 0, "duration_modifier": 0},
    {"thickness": "S", "price_modifier": 15, "duration_modifier": 15},
    {"thickness": "M", "price_modifier": 30, "duration_modifier": 30},
    {"thickness": "L", "price_modifier": 45, "duration_modifier": 45},
    {"thickness": "XL", "price_modifier": 60, "duration_modifier": 60},
]

# Extended size variations (now using descriptive length names)
EXTENDED_SIZE_VARIATIONS = [
    {"size": "Court", "price": 60, "duration_minutes": 120},
    {"size": "Moyen", "price": 80, "duration_minutes": 180},
    {"size": "Long", "price": 120, "duration_minutes": 240},
    {"size": "Très Long", "price": 160, "duration_minutes": 300},
    {"size": "Super Long", "price": 200, "duration_minutes": 360},
]


@booking_router.post("/admin/enable-thickness/{category_id}")
async def enable_thickness_for_category(category_id: str):
    """Enable thickness variations for all services in a category (like Tresses)"""
    # Get all services in this category
    services = await db.service_models.find({"category_id": category_id}).to_list(100)
    
    if not services:
        raise HTTPException(status_code=404, detail="Aucun service trouvé dans cette catégorie")
    
    updated_count = 0
    for service in services:
        # Update with thickness variations and extended sizes
        update_data = {
            "has_thickness": True,
            "thickness_variations": DEFAULT_THICKNESS_VARIATIONS,
        }
        
        # If service has old variations (S, M, L), convert to new extended format
        if service.get("variations"):
            old_variations = service["variations"]
            # Map old sizes to new extended format while keeping original prices
            new_variations = []
            for ext_var in EXTENDED_SIZE_VARIATIONS:
                # Try to find matching old variation
                matching = next((v for v in old_variations if v.get("size") == ext_var["size"]), None)
                if matching:
                    new_variations.append(matching)
                else:
                    # Use default extended variation
                    new_variations.append(ext_var)
            update_data["variations"] = new_variations
        else:
            update_data["variations"] = EXTENDED_SIZE_VARIATIONS
        
        await db.service_models.update_one(
            {"id": service["id"]},
            {"$set": update_data}
        )
        updated_count += 1
    
    return {
        "message": f"{updated_count} services mis à jour avec les variations d'épaisseur",
        "default_thickness_variations": DEFAULT_THICKNESS_VARIATIONS,
        "default_size_variations": EXTENDED_SIZE_VARIATIONS
    }


@booking_router.post("/admin/disable-thickness/{category_id}")
async def disable_thickness_for_category(category_id: str):
    """Disable thickness variations for all services in a category"""
    result = await db.service_models.update_many(
        {"category_id": category_id},
        {"$set": {"has_thickness": False, "thickness_variations": None}}
    )
    return {"message": f"{result.modified_count} services mis à jour"}


# ============== AVAILABILITY MANAGEMENT ==============

class AvailabilityUpdate(BaseModel):
    day_of_week: int  # 0=Monday, 6=Sunday
    day_name: str
    start_time: str  # HH:MM format
    end_time: str    # HH:MM format
    is_active: bool


class BlockedDate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: str  # YYYY-MM-DD format
    reason: Optional[str] = None
    all_day: bool = True
    start_time: Optional[str] = None  # If not all_day
    end_time: Optional[str] = None    # If not all_day


@booking_router.get("/admin/availability")
async def get_availability():
    """Get all availability settings"""
    availability = await db.availability.find({}, {"_id": 0}).sort("day_of_week", 1).to_list(10)
    return availability


@booking_router.put("/admin/availability/{day_of_week}")
async def update_availability(day_of_week: int, update: AvailabilityUpdate):
    """Update availability for a specific day"""
    result = await db.availability.update_one(
        {"day_of_week": day_of_week},
        {"$set": update.model_dump()},
        upsert=True
    )
    return {"message": "Disponibilité mise à jour"}


@booking_router.post("/admin/availability/bulk")
async def update_availability_bulk(updates: List[AvailabilityUpdate]):
    """Update multiple availability settings at once"""
    for update in updates:
        await db.availability.update_one(
            {"day_of_week": update.day_of_week},
            {"$set": update.model_dump()},
            upsert=True
        )
    return {"message": f"{len(updates)} disponibilités mises à jour"}


@booking_router.get("/admin/blocked-dates")
async def get_blocked_dates():
    """Get all blocked dates"""
    blocked = await db.blocked_dates.find({}, {"_id": 0}).to_list(100)
    return blocked


@booking_router.post("/admin/blocked-dates")
async def add_blocked_date(blocked: BlockedDate):
    """Block a specific date"""
    blocked_dict = blocked.model_dump()
    await db.blocked_dates.insert_one(blocked_dict)
    return {"message": "Date bloquée", "id": blocked.id}


@booking_router.delete("/admin/blocked-dates/{blocked_id}")
async def remove_blocked_date(blocked_id: str):
    """Remove a blocked date"""
    result = await db.blocked_dates.delete_one({"id": blocked_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Date bloquée non trouvée")
    
    return {"message": "Date débloquée"}


@booking_router.get("/availability/check/{date}")
async def check_date_availability(date: str):
    """Check if a specific date is available for booking"""
    try:
        check_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide (YYYY-MM-DD)")
    
    day_of_week = check_date.weekday()
    
    # Check if day is blocked
    blocked = await db.blocked_dates.find_one({"date": date})
    if blocked:
        return {"available": False, "reason": blocked.get("reason", "Date bloquée")}
    
    # Check day availability
    day_availability = await db.availability.find_one({"day_of_week": day_of_week})
    if not day_availability or not day_availability.get("is_active", False):
        return {"available": False, "reason": "Jour non disponible"}
    
    return {
        "available": True,
        "start_time": day_availability["start_time"],
        "end_time": day_availability["end_time"]
    }
