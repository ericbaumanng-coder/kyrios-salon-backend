"""
WhatsApp Notification Service for Kyrios Salon
Using Twilio WhatsApp API
"""
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')  # Twilio sandbox
KYRIOS_WHATSAPP = "+41788480867"

# Try to import twilio, but don't fail if not installed
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio not installed. WhatsApp notifications will be disabled.")


def format_phone_number(phone: str) -> str:
    """Format phone number for WhatsApp"""
    # Remove spaces and special characters
    cleaned = ''.join(filter(str.isdigit, phone.replace('+', '')))
    
    # Add Swiss country code if not present
    if not cleaned.startswith('41'):
        if cleaned.startswith('0'):
            cleaned = '41' + cleaned[1:]
        else:
            cleaned = '41' + cleaned
    
    return f"whatsapp:+{cleaned}"


def generate_order_ready_message(order: Dict) -> str:
    """Generate WhatsApp message for order ready"""
    customer_name = order.get('customer_name', 'Client')
    first_name = customer_name.split()[0] if customer_name else 'Client'
    order_number = order.get('order_number', '')
    remaining = order.get('remaining_to_pay', 0)
    delivery_method = order.get('delivery_method', 'salon')
    
    # Get first product info
    items = order.get('items', [])
    product_line = ""
    if items:
        item = items[0]
        product_line = f"✨ {item.get('product_name', '')} — {item.get('size', '')}"
    
    message = f"""🎉 Bonjour {first_name} !

Bonne nouvelle : votre commande Kyrios Salon est prête ! 💛

📦 Commande N°{order_number}
{product_line}

"""
    
    if delivery_method == 'salon':
        message += f"""📍 Vous pouvez venir la récupérer à notre salon de Fribourg dès maintenant.
💳 Solde restant : {remaining:.2f} CHF
"""
    else:
        message += """📮 Votre commande a été expédiée !
Livraison dans 2-3 jours ouvrables.
"""
    
    message += """
Des questions ? Répondez à ce message 🙂

— L'équipe Kyrios Salon"""
    
    return message


def generate_order_cancelled_message(order: Dict) -> str:
    """Generate WhatsApp message for order cancelled"""
    customer_name = order.get('customer_name', 'Client')
    first_name = customer_name.split()[0] if customer_name else 'Client'
    order_number = order.get('order_number', '')
    
    return f"""Bonjour {first_name},

Votre commande N°{order_number} a été annulée.

Contactez-nous pour plus d'informations :
https://wa.me/41788480867

— L'équipe Kyrios Salon"""


async def send_whatsapp_notification(to_phone: str, message: str) -> bool:
    """Send WhatsApp notification via Twilio"""
    
    if not TWILIO_AVAILABLE:
        logger.warning("[DEMO] WhatsApp notification would be sent (Twilio not installed)")
        logger.info(f"[DEMO] To: {to_phone}")
        logger.info(f"[DEMO] Message: {message[:100]}...")
        return True
    
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("[DEMO] Twilio credentials not configured")
        logger.info(f"[DEMO] WhatsApp to {to_phone}: {message[:100]}...")
        return True
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        to_number = format_phone_number(to_phone)
        
        whatsapp_message = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number
        )
        
        logger.info(f"WhatsApp sent successfully. SID: {whatsapp_message.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending WhatsApp: {e}")
        return False


async def notify_order_ready(order: Dict) -> bool:
    """Send order ready notification via WhatsApp"""
    phone = order.get('customer_phone')
    if not phone:
        return False
    
    message = generate_order_ready_message(order)
    return await send_whatsapp_notification(phone, message)


async def notify_order_cancelled(order: Dict) -> bool:
    """Send order cancelled notification via WhatsApp"""
    phone = order.get('customer_phone')
    if not phone:
        return False
    
    message = generate_order_cancelled_message(order)
    return await send_whatsapp_notification(phone, message)
