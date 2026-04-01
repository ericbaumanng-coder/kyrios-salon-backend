"""
Enhanced WhatsApp Notification Service for Kyrios Salon
- Twilio WhatsApp Business API integration (with demo mode)
- All notification types for salon owner
- Notification logging
"""
import os
import logging
from typing import Dict, Optional
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')
SALON_WHATSAPP = os.environ.get('SALON_WHATSAPP', 'whatsapp:+41788480867')

# Check if in demo mode
DEMO_MODE = not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN

if DEMO_MODE:
    logger.warning("WhatsApp service running in DEMO MODE - no messages will be sent")

# Try to import Twilio
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio not installed. WhatsApp notifications will be logged only.")


# ============== MESSAGE TEMPLATES ==============

def format_new_order_message(order: Dict) -> str:
    """Format message for new shop order"""
    # Extract products list
    products_list = []
    for item in order.get('items', []):
        products_list.append(f"• {item.get('product_name', 'Produit')} ({item.get('variation', '-')})")
    
    products_text = '\n'.join(products_list) if products_list else '• Voir détails dans l\'admin'
    
    message = f"""🛍 *Nouvelle commande #{order['order_number']}*

*Cliente:* {order.get('customer_name', 'N/A')}
*Téléphone:* {order.get('customer_phone', 'N/A')}

*Produits:*
{products_text}

*Total:* {order.get('total', 0):.2f} CHF
*Acompte reçu:* {order.get('amount_paid', 0):.2f} CHF
*Solde:* {order.get('remaining_to_pay', 0):.2f} CHF

📱 Voir dans l'admin pour plus de détails"""
    
    return message


def format_new_appointment_message(appointment: Dict) -> str:
    """Format message for new appointment booking"""
    message = f"""📅 *Nouveau RDV confirmé !*

*Cliente:* {appointment.get('customer_name', 'N/A')}
*Téléphone:* {appointment.get('customer_phone', 'N/A')}

*Service:* {appointment.get('service_name', 'N/A')}
*Date:* {appointment.get('appointment_date', 'N/A')}
*Heure:* {appointment.get('start_time', '')} - {appointment.get('end_time', '')}
*Durée:* {appointment.get('duration_minutes', 0)} min

*Acompte 20 CHF reçu* ✅

💰 Solde à percevoir: {appointment.get('service_price', 0) - 20:.2f} CHF"""
    
    return message


def format_appointment_reminder_message(appointment: Dict) -> str:
    """Format 24h reminder message for salon owner"""
    message = f"""⏰ *Rappel RDV demain*

*Cliente:* {appointment.get('customer_name', 'N/A')}
*Service:* {appointment.get('service_name', 'N/A')}
*Date:* {appointment.get('appointment_date', 'N/A')}
*Heure:* {appointment.get('start_time', '')}
*Durée:* {appointment.get('duration_minutes', 0)} min

📱 Tel: {appointment.get('customer_phone', 'N/A')}"""
    
    return message


def format_order_status_message(order: Dict, new_status: str) -> str:
    """Format message for order status change"""
    status_labels = {
        'processing': '📦 En préparation',
        'ready': '✅ Prête',
        'delivered': '🚚 Livrée',
        'cancelled': '❌ Annulée'
    }
    
    status_text = status_labels.get(new_status, new_status)
    
    message = f"""📋 *Statut commande mis à jour*

*Commande:* #{order['order_number']}
*Cliente:* {order.get('customer_name', 'N/A')}
*Nouveau statut:* {status_text}"""
    
    return message


# ============== SEND WHATSAPP FUNCTION ==============

async def send_whatsapp(to_number: str, message: str, related_to: str = None) -> bool:
    """
    Send a WhatsApp message via Twilio
    In demo mode, logs the message instead of sending
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    
    # Log notification to database
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    log_entry = {
        "id": f"wa_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(message) % 10000}",
        "type": "whatsapp",
        "recipient": to_number,
        "subject": None,
        "message": message[:500],  # Truncate for log
        "status": "pending",
        "related_to": related_to,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if DEMO_MODE or not TWILIO_AVAILABLE:
        # Demo mode - just log
        logger.info(f"[DEMO] Would send WhatsApp to {to_number}")
        log_entry["status"] = "sent"
        log_entry["message"] = f"[DEMO MODE] {message[:200]}..."
        await db.notification_logs.insert_one(log_entry)
        return True
    
    try:
        twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Format number for WhatsApp
        if not to_number.startswith('whatsapp:'):
            to_number = f"whatsapp:{to_number}"
        
        twilio_message = twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_FROM,
            to=to_number
        )
        
        if twilio_message.sid:
            log_entry["status"] = "sent"
            await db.notification_logs.insert_one(log_entry)
            logger.info(f"WhatsApp sent successfully: {twilio_message.sid}")
            return True
        else:
            log_entry["status"] = "failed"
            await db.notification_logs.insert_one(log_entry)
            return False
            
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        log_entry["status"] = "failed"
        log_entry["message"] = f"Error: {str(e)}"
        await db.notification_logs.insert_one(log_entry)
        return False


# ============== PUBLIC FUNCTIONS ==============

async def notify_new_order(order: Dict) -> bool:
    """Notify salon owner of new order"""
    message = format_new_order_message(order)
    return await send_whatsapp(SALON_WHATSAPP, message, order.get('id'))


async def notify_new_appointment(appointment: Dict) -> bool:
    """Notify salon owner of new appointment"""
    message = format_new_appointment_message(appointment)
    return await send_whatsapp(SALON_WHATSAPP, message, appointment.get('id'))


async def notify_appointment_reminder(appointment: Dict) -> bool:
    """Send 24h reminder to salon owner"""
    message = format_appointment_reminder_message(appointment)
    return await send_whatsapp(SALON_WHATSAPP, message, appointment.get('id'))


async def notify_order_status_change(order: Dict, new_status: str) -> bool:
    """Notify salon owner of order status change"""
    message = format_order_status_message(order, new_status)
    return await send_whatsapp(SALON_WHATSAPP, message, order.get('id'))


# ============== CUSTOMER NOTIFICATIONS (Optional) ==============

async def notify_customer_order_ready(order: Dict) -> bool:
    """Notify customer that order is ready (optional)"""
    phone = order.get('customer_phone', '')
    if not phone:
        return False
    
    message = f"""🎉 *Bonne nouvelle de Kyrios Salon !*

Votre commande #{order['order_number']} est prête !

📍 *Retrait:*
Rue du Pont-de-Perrette 8
1700 Fribourg

🕒 *Horaires:*
Mer-Sam 7h30-18h30

{'💰 Solde à régler: ' + str(order.get("remaining_to_pay", 0)) + ' CHF' if order.get('remaining_to_pay', 0) > 0 else ''}

À très bientôt !
✨ L'équipe Kyrios Salon"""
    
    return await send_whatsapp(phone, message, order.get('id'))
