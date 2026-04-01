"""
Enhanced Email Service for Kyrios Salon
- Luxurious HTML email templates
- SendGrid/SMTP integration (with demo mode)
- All 5 email types + notification logging
"""
import os
import logging
import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Email Configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
SMTP_USER = os.environ.get('SMTP_USER', 'info@kyrios-salon.ch')
SMTP_PASS = os.environ.get('SMTP_PASS', '')

# Salon Information
SALON_NAME = "Kyrios Salon"
SALON_ADDRESS = "Rue du Pont-de-Perrette 8, 1700 Fribourg"
SALON_PHONE = "+41 78 848 08 67"
SALON_EMAIL = "clients@kyrios-salon.ch"
SALON_HOURS = "Mer-Sam 7h30-18h30"
WHATSAPP_LINK = "https://wa.me/41788480867"

# Check if in demo mode
DEMO_MODE = not SENDGRID_API_KEY and not SMTP_PASS

if DEMO_MODE:
    logger.warning("Email service running in DEMO MODE - no emails will be sent")


def get_email_base_styles():
    """Return common email styles"""
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');
        
        body {
            font-family: 'Inter', Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #1a1a1a;
        }
        
        .email-container {
            max-width: 600px;
            margin: 0 auto;
            background-color: #1a1a1a;
        }
        
        .header {
            background-color: #1a1a1a;
            padding: 30px;
            text-align: center;
            border-bottom: 1px solid #C9A84C;
        }
        
        .logo {
            font-family: 'Playfair Display', Georgia, serif;
            color: #C9A84C;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: 2px;
        }
        
        .content {
            background-color: #FAFAFA;
            padding: 40px 30px;
        }
        
        h1 {
            font-family: 'Playfair Display', Georgia, serif;
            color: #1a1a1a;
            font-size: 24px;
            margin: 0 0 20px 0;
        }
        
        h2 {
            font-family: 'Playfair Display', Georgia, serif;
            color: #C9A84C;
            font-size: 18px;
            margin: 25px 0 15px 0;
        }
        
        p {
            color: #333;
            font-size: 15px;
            line-height: 1.6;
            margin: 0 0 15px 0;
        }
        
        .highlight-box {
            background-color: #1a1a1a;
            color: #FAFAFA;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #C9A84C;
        }
        
        .highlight-box strong {
            color: #C9A84C;
        }
        
        .btn-gold {
            display: inline-block;
            background: linear-gradient(135deg, #C9A84C 0%, #E8C96A 100%);
            color: #1a1a1a !important;
            text-decoration: none;
            padding: 14px 30px;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 10px 0;
        }
        
        .btn-whatsapp {
            display: inline-block;
            background-color: #25D366;
            color: #fff !important;
            text-decoration: none;
            padding: 12px 25px;
            font-weight: 600;
            font-size: 14px;
            margin: 10px 0;
        }
        
        .product-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        .product-table th {
            background-color: #1a1a1a;
            color: #C9A84C;
            padding: 12px;
            text-align: left;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        .product-table td {
            padding: 12px;
            border-bottom: 1px solid #eee;
            font-size: 14px;
        }
        
        .total-row td {
            font-weight: 600;
            border-top: 2px solid #1a1a1a;
        }
        
        .footer {
            background-color: #1a1a1a;
            padding: 30px;
            text-align: center;
            color: #888;
            font-size: 12px;
        }
        
        .footer a {
            color: #C9A84C;
            text-decoration: none;
        }
        
        .success-icon {
            width: 60px;
            height: 60px;
            background-color: #22c55e;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
        }
        
        .appointment-card {
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            color: #FAFAFA;
            padding: 25px;
            margin: 20px 0;
        }
        
        .appointment-card .detail {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(201, 168, 76, 0.2);
        }
        
        .appointment-card .label {
            color: #888;
        }
        
        .appointment-card .value {
            color: #C9A84C;
            font-weight: 500;
        }
    </style>
    """


def get_email_header():
    """Return email header HTML"""
    return f"""
    <div class="header">
        <div class="logo">{SALON_NAME}</div>
        <p style="color: #888; font-size: 12px; margin: 10px 0 0 0;">Extensions & Perruques de Luxe</p>
    </div>
    """


def get_email_footer():
    """Return email footer HTML"""
    return f"""
    <div class="footer">
        <p style="color: #C9A84C; font-size: 14px; margin-bottom: 15px;">✦ {SALON_NAME} ✦</p>
        <p>{SALON_ADDRESS}</p>
        <p>{SALON_PHONE} • {SALON_EMAIL}</p>
        <p style="margin-top: 15px;">
            <a href="{WHATSAPP_LINK}">WhatsApp</a> • 
            <a href="https://kyrios-salon.ch">Site Web</a>
        </p>
        <p style="margin-top: 20px; color: #666;">
            Horaires: {SALON_HOURS}
        </p>
    </div>
    """


# ============== EMAIL TEMPLATES ==============

def email_order_confirmation(order: Dict) -> tuple:
    """Email 1: Order Confirmation"""
    subject = f"✨ Votre commande Kyrios Salon est confirmée — N°{order['order_number']}"
    
    # Build products table
    products_html = ""
    for item in order.get('items', []):
        products_html += f"""
        <tr>
            <td>{item.get('product_name', 'Produit')}</td>
            <td>{item.get('variation', '-')}</td>
            <td style="text-align: center;">{item.get('quantity', 1)}</td>
            <td style="text-align: right;">{item.get('unit_price', 0):.2f} CHF</td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_email_base_styles()}
    </head>
    <body>
        <div class="email-container">
            {get_email_header()}
            
            <div class="content">
                <h1>Merci pour votre commande !</h1>
                
                <p>Bonjour <strong>{order.get('customer_name', '').split()[0]}</strong>,</p>
                
                <p>Nous avons bien reçu votre commande et nous allons la préparer avec le plus grand soin.</p>
                
                <div class="highlight-box">
                    <strong>Numéro de commande:</strong> {order['order_number']}<br>
                    <strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y à %H:%M')}
                </div>
                
                <h2>Récapitulatif de votre commande</h2>
                
                <table class="product-table">
                    <thead>
                        <tr>
                            <th>Produit</th>
                            <th>Taille</th>
                            <th style="text-align: center;">Qté</th>
                            <th style="text-align: right;">Prix</th>
                        </tr>
                    </thead>
                    <tbody>
                        {products_html}
                        <tr class="total-row">
                            <td colspan="3"><strong>Sous-total</strong></td>
                            <td style="text-align: right;"><strong>{order.get('total', 0):.2f} CHF</strong></td>
                        </tr>
                        <tr>
                            <td colspan="3" style="color: #22c55e;">Acompte versé</td>
                            <td style="text-align: right; color: #22c55e;">-{order.get('amount_paid', 0):.2f} CHF</td>
                        </tr>
                        <tr>
                            <td colspan="3" style="color: #C9A84C;"><strong>Solde restant</strong></td>
                            <td style="text-align: right; color: #C9A84C;"><strong>{order.get('remaining_to_pay', 0):.2f} CHF</strong></td>
                        </tr>
                    </tbody>
                </table>
                
                <h2>Mode de livraison</h2>
                <p>{order.get('delivery_method', 'Retrait au salon')}</p>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{WHATSAPP_LINK}" class="btn-whatsapp">Une question ? Contactez-nous</a>
                </p>
            </div>
            
            {get_email_footer()}
        </div>
    </body>
    </html>
    """
    
    return subject, html


def email_deposit_received(order: Dict) -> tuple:
    """Email 2: Deposit Received"""
    subject = f"💛 Acompte reçu — Votre commande est en préparation"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_email_base_styles()}
    </head>
    <body>
        <div class="email-container">
            {get_email_header()}
            
            <div class="content">
                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="width: 60px; height: 60px; background-color: #22c55e; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                        <span style="font-size: 30px; color: white;">✓</span>
                    </div>
                    <h1 style="color: #22c55e;">Acompte reçu avec succès !</h1>
                </div>
                
                <p>Bonjour <strong>{order.get('customer_name', '').split()[0]}</strong>,</p>
                
                <p>Nous confirmons la réception de votre acompte de <strong style="color: #C9A84C;">{order.get('amount_paid', 50):.2f} CHF</strong> pour votre commande.</p>
                
                <div class="highlight-box">
                    <strong>Commande:</strong> {order['order_number']}<br>
                    <strong>Acompte reçu:</strong> {order.get('amount_paid', 50):.2f} CHF<br>
                    <strong>Solde restant:</strong> {order.get('remaining_to_pay', 0):.2f} CHF
                </div>
                
                <p>Notre équipe prépare votre commande avec amour et attention. Nous vous tiendrons informée dès qu'elle sera prête !</p>
                
                <p style="background-color: #FEF3C7; padding: 15px; border-radius: 4px; color: #92400E;">
                    💡 <strong>Le solde de {order.get('remaining_to_pay', 0):.2f} CHF</strong> sera à régler lors du retrait de votre commande.
                </p>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{WHATSAPP_LINK}" class="btn-whatsapp">Une question sur WhatsApp</a>
                </p>
            </div>
            
            {get_email_footer()}
        </div>
    </body>
    </html>
    """
    
    return subject, html


def email_order_ready(order: Dict) -> tuple:
    """Email 3: Order Ready"""
    subject = f"🎉 Votre commande est prête — Kyrios Salon"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_email_base_styles()}
    </head>
    <body>
        <div class="email-container">
            {get_email_header()}
            
            <div class="content">
                <div style="text-align: center; margin-bottom: 30px;">
                    <span style="font-size: 50px;">🎉</span>
                    <h1>Votre commande est prête !</h1>
                </div>
                
                <p>Bonjour <strong>{order.get('customer_name', '').split()[0]}</strong>,</p>
                
                <p>Excellente nouvelle ! Votre commande <strong>{order['order_number']}</strong> est prête et vous attend au salon.</p>
                
                <div class="highlight-box">
                    <strong style="font-size: 18px;">📍 Venez la récupérer:</strong><br><br>
                    <strong>{SALON_ADDRESS}</strong><br>
                    <span style="color: #888;">Horaires: {SALON_HOURS}</span>
                </div>
                
                {'<p style="background-color: #FEF3C7; padding: 15px; color: #92400E;"><strong>💰 Solde à régler:</strong> ' + str(order.get("remaining_to_pay", 0)) + ' CHF</p>' if order.get('remaining_to_pay', 0) > 0 else ''}
                
                <p>Nous avons hâte de vous voir !</p>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{WHATSAPP_LINK}" class="btn-whatsapp">Prévenir de mon arrivée</a>
                </p>
            </div>
            
            {get_email_footer()}
        </div>
    </body>
    </html>
    """
    
    return subject, html


def email_appointment_confirmed(appointment: Dict) -> tuple:
    """Email 4: Appointment Confirmation"""
    subject = f"📅 RDV confirmé — {appointment['service_name']} le {appointment['appointment_date']}"
    
    # Format date
    date_obj = datetime.strptime(appointment['appointment_date'], '%Y-%m-%d')
    formatted_date = date_obj.strftime('%A %d %B %Y').capitalize()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_email_base_styles()}
    </head>
    <body>
        <div class="email-container">
            {get_email_header()}
            
            <div class="content">
                <div style="text-align: center; margin-bottom: 30px;">
                    <span style="font-size: 50px;">📅</span>
                    <h1>Rendez-vous confirmé !</h1>
                </div>
                
                <p>Bonjour <strong>{appointment.get('customer_name', '').split()[0]}</strong>,</p>
                
                <p>Votre rendez-vous est confirmé. Nous avons hâte de vous accueillir !</p>
                
                <div class="appointment-card">
                    <div class="detail">
                        <span class="label">Service</span>
                        <span class="value">{appointment['service_name']}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Date</span>
                        <span class="value">{formatted_date}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Heure</span>
                        <span class="value">{appointment['start_time']} - {appointment['end_time']}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Durée estimée</span>
                        <span class="value">{appointment['duration_minutes'] // 60}h{appointment['duration_minutes'] % 60 if appointment['duration_minutes'] % 60 > 0 else ''}</span>
                    </div>
                    <div class="detail" style="border-bottom: none;">
                        <span class="label">Acompte payé</span>
                        <span class="value" style="color: #22c55e;">✓ 20 CHF</span>
                    </div>
                </div>
                
                <div class="highlight-box">
                    <strong>📍 Adresse:</strong><br>
                    {SALON_ADDRESS}
                </div>
                
                <p style="background-color: #FEF3C7; padding: 15px; color: #92400E;">
                    💰 <strong>Solde à régler au salon:</strong> {appointment['service_price'] - 20:.2f} CHF
                </p>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="#" class="btn-gold">Ajouter à mon calendrier</a>
                </p>
                
                <p style="text-align: center;">
                    <a href="{WHATSAPP_LINK}" class="btn-whatsapp">Contacter sur WhatsApp</a>
                </p>
            </div>
            
            {get_email_footer()}
        </div>
    </body>
    </html>
    """
    
    return subject, html


def email_appointment_reminder(appointment: Dict) -> tuple:
    """Email 5: Appointment Reminder (24h before)"""
    subject = f"⏰ Rappel — Votre RDV demain à {appointment['start_time']} chez Kyrios Salon"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_email_base_styles()}
    </head>
    <body>
        <div class="email-container">
            {get_email_header()}
            
            <div class="content">
                <div style="text-align: center; margin-bottom: 30px;">
                    <span style="font-size: 50px;">⏰</span>
                    <h1>Rappel de votre rendez-vous</h1>
                </div>
                
                <p>Bonjour <strong>{appointment.get('customer_name', '').split()[0]}</strong>,</p>
                
                <p>C'est demain ! Nous vous attendons pour votre rendez-vous.</p>
                
                <div class="appointment-card">
                    <div class="detail">
                        <span class="label">Service</span>
                        <span class="value">{appointment['service_name']}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Demain à</span>
                        <span class="value" style="font-size: 20px;">{appointment['start_time']}</span>
                    </div>
                    <div class="detail" style="border-bottom: none;">
                        <span class="label">Durée</span>
                        <span class="value">{appointment['duration_minutes'] // 60}h{appointment['duration_minutes'] % 60 if appointment['duration_minutes'] % 60 > 0 else ''}</span>
                    </div>
                </div>
                
                <div class="highlight-box">
                    <strong>📍 Nous vous attendons:</strong><br>
                    {SALON_ADDRESS}<br>
                    <span style="color: #888;">Merci d'arriver 5 minutes avant l'heure prévue</span>
                </div>
                
                <p>À très bientôt !</p>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{WHATSAPP_LINK}" class="btn-whatsapp">Besoin de modifier ? WhatsApp</a>
                </p>
            </div>
            
            {get_email_footer()}
        </div>
    </body>
    </html>
    """
    
    return subject, html


# ============== SEND EMAIL FUNCTION ==============

async def send_email(to_email: str, subject: str, html_content: str, related_to: str = None) -> bool:
    """
    Send an email using SendGrid or SMTP
    In demo mode, logs the email instead of sending
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    
    # Log notification to database
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    log_entry = {
        "id": f"log_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(to_email) % 10000}",
        "type": "email",
        "recipient": to_email,
        "subject": subject,
        "message": f"HTML email ({len(html_content)} chars)",
        "status": "pending",
        "related_to": related_to,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if DEMO_MODE:
        # Demo mode - just log
        logger.info(f"[DEMO] Would send email to {to_email}: {subject}")
        log_entry["status"] = "sent"
        log_entry["message"] = f"[DEMO MODE] {subject}"
        await db.notification_logs.insert_one(log_entry)
        return True
    
    try:
        if SENDGRID_API_KEY:
            # Use SendGrid
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
            message = Mail(
                from_email=Email(SMTP_USER, SALON_NAME),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                log_entry["status"] = "sent"
                await db.notification_logs.insert_one(log_entry)
                return True
            else:
                log_entry["status"] = "failed"
                await db.notification_logs.insert_one(log_entry)
                return False
                
        elif SMTP_HOST and SMTP_PASS:
            # Use SMTP
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{SALON_NAME} <{SMTP_USER}>"
            msg['To'] = to_email
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_USER, to_email, msg.as_string())
            
            log_entry["status"] = "sent"
            await db.notification_logs.insert_one(log_entry)
            return True
        else:
            # Fallback to demo mode
            logger.warning(f"No email credentials - logging only: {subject}")
            log_entry["status"] = "sent"
            log_entry["message"] = f"[NO CREDENTIALS] {subject}"
            await db.notification_logs.insert_one(log_entry)
            return True
            
    except Exception as e:
        logger.error(f"Email send error: {e}")
        log_entry["status"] = "failed"
        log_entry["message"] = f"Error: {str(e)}"
        await db.notification_logs.insert_one(log_entry)
        return False


# ============== PUBLIC FUNCTIONS ==============

async def send_order_confirmation_email(order: Dict) -> bool:
    """Send order confirmation email"""
    subject, html = email_order_confirmation(order)
    return await send_email(order['customer_email'], subject, html, order.get('id'))


async def send_deposit_received_email(order: Dict) -> bool:
    """Send deposit received email"""
    subject, html = email_deposit_received(order)
    return await send_email(order['customer_email'], subject, html, order.get('id'))


async def send_order_ready_email(order: Dict) -> bool:
    """Send order ready email"""
    subject, html = email_order_ready(order)
    return await send_email(order['customer_email'], subject, html, order.get('id'))


async def send_appointment_confirmation_email(appointment: Dict) -> bool:
    """Send appointment confirmation email"""
    subject, html = email_appointment_confirmed(appointment)
    return await send_email(appointment['customer_email'], subject, html, appointment.get('id'))


async def send_appointment_reminder_email(appointment: Dict) -> bool:
    """Send appointment reminder email (24h before)"""
    subject, html = email_appointment_reminder(appointment)
    return await send_email(appointment['customer_email'], subject, html, appointment.get('id'))
