"""
Appointment Reminder Scheduler for Kyrios Salon
- Sends automatic reminders 24h before appointments
- Email to customer
- WhatsApp to customer and salon owner
- Runs in background using APScheduler
"""
import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'test_database')

# Scheduler instance
scheduler = None


async def get_db():
    """Get database connection"""
    client = AsyncIOMotorClient(mongo_url)
    return client[db_name]


async def send_reminder_email(appointment: dict) -> bool:
    """Send reminder email to customer"""
    try:
        from email_service_enhanced import send_appointment_reminder_email
        return await send_appointment_reminder_email(appointment)
    except Exception as e:
        logger.error(f"Failed to send reminder email: {e}")
        return False


async def send_reminder_whatsapp_customer(appointment: dict) -> bool:
    """Send WhatsApp reminder to customer"""
    try:
        from whatsapp_service_enhanced import send_whatsapp
        
        customer_phone = appointment.get('customer_phone', '')
        if not customer_phone:
            logger.warning(f"No phone number for appointment {appointment.get('id')}")
            return False
        
        # Format phone number
        phone = customer_phone.replace(' ', '').replace('-', '')
        if not phone.startswith('+'):
            phone = f"+{phone}" if phone.startswith('41') else f"+41{phone}"
        
        message = f"""⏰ *Rappel — Votre RDV demain chez Kyrios Salon*

Bonjour {appointment.get('customer_name', '').split()[0]} !

Nous vous attendons demain pour votre rendez-vous :

📋 *Service:* {appointment.get('service_name', 'N/A')}
🕐 *Heure:* {appointment.get('start_time', '')}
⏱️ *Durée:* {appointment.get('duration_minutes', 0)} min

📍 *Adresse:*
Rue du Pont-de-Perrette 8
1700 Fribourg

💰 *Solde à régler:* {appointment.get('service_price', 0) - 20:.2f} CHF

Merci d'arriver 5 minutes avant l'heure prévue.

À demain ! ✨
L'équipe Kyrios Salon"""
        
        return await send_whatsapp(phone, message, appointment.get('id'))
        
    except Exception as e:
        logger.error(f"Failed to send WhatsApp reminder to customer: {e}")
        return False


async def send_reminder_whatsapp_salon(appointment: dict) -> bool:
    """Send WhatsApp reminder to salon owner"""
    try:
        from whatsapp_service_enhanced import notify_appointment_reminder
        return await notify_appointment_reminder(appointment)
    except Exception as e:
        logger.error(f"Failed to send WhatsApp reminder to salon: {e}")
        return False


async def check_and_send_reminders():
    """
    Check for appointments that need reminders (24h before)
    and send notifications
    """
    logger.info("🔔 Running appointment reminder check...")
    
    try:
        db = await get_db()
        
        # Calculate the time window for reminders
        # We want appointments that are between 23h and 25h from now
        now = datetime.now(timezone.utc)
        reminder_start = now + timedelta(hours=23)
        reminder_end = now + timedelta(hours=25)
        
        # Format dates for comparison
        tomorrow_date = (now + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Find appointments for tomorrow that:
        # 1. Are confirmed
        # 2. Haven't received a reminder yet
        appointments = await db.appointments.find({
            "appointment_date": tomorrow_date,
            "status": "confirmed",
            "reminder_sent": {"$ne": True}
        }, {"_id": 0}).to_list(100)
        
        if not appointments:
            logger.info("No appointments need reminders at this time")
            return
        
        logger.info(f"Found {len(appointments)} appointments needing reminders")
        
        for appointment in appointments:
            appointment_id = appointment.get('id')
            customer_name = appointment.get('customer_name', 'Cliente')
            service_name = appointment.get('service_name', 'Service')
            start_time = appointment.get('start_time', '')
            
            logger.info(f"Sending reminders for appointment {appointment_id}: {customer_name} - {service_name} at {start_time}")
            
            # Send all reminders
            email_sent = await send_reminder_email(appointment)
            whatsapp_customer_sent = await send_reminder_whatsapp_customer(appointment)
            whatsapp_salon_sent = await send_reminder_whatsapp_salon(appointment)
            
            # Mark reminder as sent if at least one notification was successful
            if email_sent or whatsapp_customer_sent or whatsapp_salon_sent:
                await db.appointments.update_one(
                    {"id": appointment_id},
                    {"$set": {
                        "reminder_sent": True,
                        "reminder_sent_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                logger.info(f"✅ Reminders sent for appointment {appointment_id}")
            else:
                logger.warning(f"⚠️ All reminders failed for appointment {appointment_id}")
        
    except Exception as e:
        logger.error(f"Error in reminder check: {e}")


def start_scheduler():
    """Start the appointment reminder scheduler"""
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already running")
        return
    
    scheduler = AsyncIOScheduler()
    
    # Run the reminder check every hour
    scheduler.add_job(
        check_and_send_reminders,
        trigger=IntervalTrigger(hours=1),
        id='appointment_reminders',
        name='Check and send appointment reminders',
        replace_existing=True
    )
    
    # Also run immediately on startup
    scheduler.add_job(
        check_and_send_reminders,
        id='appointment_reminders_startup',
        name='Initial reminder check on startup'
    )
    
    scheduler.start()
    logger.info("📅 Appointment reminder scheduler started (running every hour)")


def stop_scheduler():
    """Stop the scheduler"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Appointment reminder scheduler stopped")


# Manual trigger function for testing
async def trigger_reminder_check():
    """Manually trigger a reminder check (for testing)"""
    await check_and_send_reminders()


# Function to send test reminder for a specific appointment
async def send_test_reminder(appointment_id: str) -> dict:
    """Send a test reminder for a specific appointment"""
    db = await get_db()
    
    appointment = await db.appointments.find_one({"id": appointment_id}, {"_id": 0})
    
    if not appointment:
        return {"success": False, "error": "Appointment not found"}
    
    results = {
        "appointment_id": appointment_id,
        "customer_name": appointment.get('customer_name'),
        "email_sent": await send_reminder_email(appointment),
        "whatsapp_customer_sent": await send_reminder_whatsapp_customer(appointment),
        "whatsapp_salon_sent": await send_reminder_whatsapp_salon(appointment)
    }
    
    return results
