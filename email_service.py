"""
Email Templates and Service for Kyrios Salon
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Email Configuration
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.hostinger.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
SMTP_USER = os.environ.get('SMTP_USER', 'clients@kyrios-salon.ch')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
FROM_NAME = "Kyrios Salon"
FROM_EMAIL = "clients@kyrios-salon.ch"

WHATSAPP_LINK = "https://wa.me/41788480867"

def get_base_template(title: str, content: str, show_footer: bool = True) -> str:
    """Base HTML template for all emails"""
    footer_html = '''
        <div class="footer">
            <p><a href="https://kyrios-salon.ch">kyrios-salon.ch</a> | Fribourg, Suisse</p>
            <div class="contact">
                <p><a href="mailto:clients@kyrios-salon.ch">clients@kyrios-salon.ch</a></p>
                <p>+41 78 848 08 67</p>
            </div>
            <p style="margin-top: 20px; color: #666;">&copy; 2026 Kyrios Salon / Lyrias'Hair</p>
        </div>
        ''' if show_footer else ''
    
    return f'''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600&family=Inter:wght@300;400;500;600&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #f5f5f5;
            color: #1a1a1a;
            line-height: 1.6;
        }}
        
        .email-wrapper {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
        }}
        
        .header {{
            background-color: #0D0D0D;
            padding: 32px 24px;
            text-align: center;
        }}
        
        .logo {{
            font-family: 'Playfair Display', serif;
            font-size: 32px;
            color: #C9A84C;
            margin-bottom: 8px;
            font-style: italic;
        }}
        
        .header-line {{
            width: 80px;
            height: 2px;
            background: linear-gradient(90deg, #C9A84C, #E8C96A);
            margin: 0 auto;
        }}
        
        .content {{
            background-color: #FAFAFA;
            padding: 40px 32px;
        }}
        
        .title {{
            font-family: 'Playfair Display', serif;
            font-size: 28px;
            color: #C9A84C;
            margin-bottom: 24px;
            text-align: center;
        }}
        
        .text {{
            font-size: 15px;
            color: #4a4a4a;
            margin-bottom: 20px;
            text-align: center;
        }}
        
        .table-wrapper {{
            margin: 24px 0;
            border-radius: 4px;
            overflow: hidden;
            border: 1px solid #e5e5e5;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            background-color: #0D0D0D;
            color: #C9A84C;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 14px 12px;
            text-align: left;
        }}
        
        td {{
            padding: 14px 12px;
            font-size: 14px;
            border-bottom: 1px solid #e5e5e5;
        }}
        
        tr:nth-child(even) {{
            background-color: #F5E6D3;
        }}
        
        tr:nth-child(odd) {{
            background-color: #ffffff;
        }}
        
        .total-row {{
            background-color: #0D0D0D !important;
        }}
        
        .total-row td {{
            color: #C9A84C;
            font-weight: 600;
            font-size: 16px;
        }}
        
        .deposit-box {{
            background: linear-gradient(135deg, rgba(201,168,76,0.15) 0%, rgba(248,244,238,1) 100%);
            border-left: 4px solid #C9A84C;
            padding: 20px;
            margin: 24px 0;
            border-radius: 0 4px 4px 0;
        }}
        
        .deposit-box p {{
            margin: 8px 0;
            font-size: 14px;
        }}
        
        .deposit-box .paid {{
            color: #22c55e;
            font-weight: 600;
        }}
        
        .deposit-box .remaining {{
            color: #C9A84C;
            font-weight: 600;
        }}
        
        .info-box {{
            background-color: #ffffff;
            border: 1px solid #e5e5e5;
            padding: 20px;
            margin: 24px 0;
            border-radius: 4px;
            text-align: center;
        }}
        
        .info-box .icon {{
            font-size: 24px;
            margin-bottom: 12px;
        }}
        
        .btn {{
            display: inline-block;
            background: linear-gradient(135deg, #C9A84C 0%, #A07830 100%);
            color: #0D0D0D !important;
            text-decoration: none;
            padding: 16px 32px;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-radius: 0;
            margin: 24px 0;
        }}
        
        .btn:hover {{
            background: linear-gradient(135deg, #E8C96A 0%, #C9A84C 100%);
        }}
        
        .btn-whatsapp {{
            background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
            color: #ffffff !important;
        }}
        
        .order-number {{
            font-family: 'Playfair Display', serif;
            font-size: 20px;
            color: #C9A84C;
            text-align: center;
            padding: 16px;
            background-color: #0D0D0D;
            margin: 24px 0;
            border-radius: 4px;
        }}
        
        .delivery-info {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 16px;
            background-color: #ffffff;
            border: 1px solid #e5e5e5;
            border-radius: 4px;
            margin: 16px 0;
        }}
        
        .success-icon {{
            width: 80px;
            height: 80px;
            background-color: #22c55e;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
            font-size: 40px;
            color: white;
        }}
        
        .celebration {{
            text-align: center;
            position: relative;
        }}
        
        .confetti {{
            position: absolute;
            width: 10px;
            height: 10px;
            background-color: #C9A84C;
            animation: confetti-fall 3s ease-in-out infinite;
        }}
        
        @keyframes confetti-fall {{
            0% {{ transform: translateY(-10px) rotate(0deg); opacity: 1; }}
            100% {{ transform: translateY(100px) rotate(360deg); opacity: 0; }}
        }}
        
        .footer {{
            background-color: #0D0D0D;
            padding: 32px 24px;
            text-align: center;
            color: #9ca3af;
            font-size: 13px;
        }}
        
        .footer a {{
            color: #C9A84C;
            text-decoration: none;
        }}
        
        .footer p {{
            margin: 8px 0;
        }}
        
        .footer .contact {{
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid #333;
        }}
        
        .delay-info {{
            text-align: center;
            color: #6b7280;
            font-size: 13px;
            margin-top: 24px;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <!-- Header -->
        <div class="header">
            <div class="logo">Kyrios Salon</div>
            <div class="header-line"></div>
        </div>
        
        <!-- Content -->
        <div class="content">
            {content}
        </div>
        
        <!-- Footer -->
        {footer_html}
    </div>
</body>
</html>
'''

def generate_order_confirmation_email(order: Dict) -> str:
    """Generate order confirmation email (Email 1)"""
    customer_name = order.get('customer_name', 'Client')
    first_name = customer_name.split()[0] if customer_name else 'Client'
    order_number = order.get('order_number', '')
    items = order.get('items', [])
    total = order.get('total', 0)
    amount_paid = order.get('amount_paid', 0)
    remaining = order.get('remaining_to_pay', 0)
    delivery_method = order.get('delivery_method', 'salon')
    
    # Build products table
    products_rows = ""
    for item in items:
        coloration = "Oui" if item.get('coloration') else "Non"
        products_rows += f'''
        <tr>
            <td>{item.get('product_name', '')}</td>
            <td>{item.get('size', '')}</td>
            <td>{item.get('lace_type', '')}</td>
            <td>{coloration}</td>
            <td style="text-align: right; font-weight: 500;">{item.get('total_price', 0):.2f} CHF</td>
        </tr>
        '''
    
    # Deposit section
    deposit_section = ""
    if remaining > 0:
        deposit_section = f'''
        <div class="deposit-box">
            <p class="paid">✅ Acompte payé : {amount_paid:.2f} CHF</p>
            <p class="remaining">💳 Solde restant : {remaining:.2f} CHF (à la livraison)</p>
        </div>
        '''
    
    # Delivery info
    if delivery_method == 'salon':
        delivery_html = '''
        <div class="info-box">
            <div class="icon">📍</div>
            <p><strong>Retrait au salon</strong></p>
            <p style="color: #6b7280; font-size: 13px;">Fribourg, Suisse</p>
        </div>
        '''
    else:
        delivery_html = '''
        <div class="info-box">
            <div class="icon">📮</div>
            <p><strong>Expédition postale</strong></p>
            <p style="color: #6b7280; font-size: 13px;">Livraison en Suisse</p>
        </div>
        '''
    
    content = f'''
    <h1 class="title">Merci {first_name} ! ✨</h1>
    <p class="text">Votre commande a bien été reçue.<br>Voici votre récapitulatif :</p>
    
    <div class="order-number">Commande N°{order_number}</div>
    
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>Produit</th>
                    <th>Longueur</th>
                    <th>Lace</th>
                    <th>Coloration</th>
                    <th style="text-align: right;">Prix</th>
                </tr>
            </thead>
            <tbody>
                {products_rows}
                <tr class="total-row">
                    <td colspan="4"><strong>Total</strong></td>
                    <td style="text-align: right;"><strong>{total:.2f} CHF</strong></td>
                </tr>
            </tbody>
        </table>
    </div>
    
    {deposit_section}
    {delivery_html}
    
    <div style="text-align: center;">
        <a href="{WHATSAPP_LINK}?text=Bonjour, j'ai une question sur ma commande N°{order_number}" class="btn btn-whatsapp">
            💬 Une question ? Écrivez-nous sur WhatsApp
        </a>
    </div>
    
    <p class="delay-info">Votre commande sera prête dans 3 à 7 jours ouvrables.</p>
    '''
    
    return get_base_template(f"Commande confirmée N°{order_number}", content)


def generate_deposit_received_email(order: Dict) -> str:
    """Generate deposit received email (Email 2)"""
    customer_name = order.get('customer_name', 'Client')
    first_name = customer_name.split()[0] if customer_name else 'Client'
    order_number = order.get('order_number', '')
    remaining = order.get('remaining_to_pay', 0)
    
    content = f'''
    <div class="success-icon">✅</div>
    
    <h1 class="title">Votre acompte de 50 CHF a été reçu !</h1>
    
    <p class="text">Bonjour {first_name},<br>Votre commande est maintenant en cours de préparation.</p>
    
    <div class="order-number">Commande N°{order_number}</div>
    
    <div class="deposit-box">
        <p><strong>📦 Nous vous contacterons sur WhatsApp dès que votre commande sera prête.</strong></p>
        <p style="margin-top: 12px;">Solde restant à payer : <span class="remaining">{remaining:.2f} CHF</span></p>
    </div>
    
    <div style="text-align: center;">
        <a href="{WHATSAPP_LINK}?text=Bonjour, j'ai une question sur ma commande N°{order_number}" class="btn btn-whatsapp">
            💬 Nous contacter sur WhatsApp
        </a>
    </div>
    '''
    
    return get_base_template(f"Acompte reçu — Commande N°{order_number}", content)


def generate_order_ready_email(order: Dict) -> str:
    """Generate order ready email (Email 3)"""
    customer_name = order.get('customer_name', 'Client')
    first_name = customer_name.split()[0] if customer_name else 'Client'
    order_number = order.get('order_number', '')
    remaining = order.get('remaining_to_pay', 0)
    delivery_method = order.get('delivery_method', 'salon')
    
    # Get first product name
    items = order.get('items', [])
    product_info = ""
    if items:
        item = items[0]
        product_info = f"{item.get('product_name', '')} — {item.get('size', '')}"
    
    if delivery_method == 'salon':
        delivery_content = f'''
        <div class="deposit-box">
            <p><strong>📍 Venez nous rendre visite à Fribourg</strong></p>
            <p style="margin-top: 8px;">N'oubliez pas votre solde de <span class="remaining">{remaining:.2f} CHF</span></p>
            <p style="margin-top: 12px; color: #6b7280; font-size: 13px;">
                Kyrios Salon<br>
                Fribourg, Suisse
            </p>
        </div>
        
        <div style="text-align: center;">
            <a href="https://maps.google.com/?q=Kyrios+Salon+Fribourg+Suisse" class="btn" target="_blank">
                📍 Voir sur Google Maps
            </a>
        </div>
        '''
    else:
        delivery_content = f'''
        <div class="deposit-box">
            <p><strong>📮 Votre commande a été expédiée !</strong></p>
            <p style="margin-top: 8px;">Livraison estimée dans 2-3 jours ouvrables.</p>
            {"" if remaining <= 0 else f'<p style="margin-top: 8px;">Solde à payer à la livraison : <span class="remaining">{remaining:.2f} CHF</span></p>'}
        </div>
        '''
    
    content = f'''
    <div class="celebration">
        <h1 class="title" style="font-size: 32px;">Votre commande est prête ! 🎉</h1>
    </div>
    
    <p class="text">Bonjour {first_name},<br>Excellente nouvelle !</p>
    
    <div class="order-number">
        Commande N°{order_number}<br>
        <span style="font-size: 14px; font-family: Inter, sans-serif;">✨ {product_info}</span>
    </div>
    
    {delivery_content}
    
    <div style="text-align: center;">
        <a href="{WHATSAPP_LINK}?text=Bonjour, je souhaite confirmer mon heure de passage pour la commande N°{order_number}" class="btn btn-whatsapp">
            💬 Confirmer sur WhatsApp
        </a>
    </div>
    '''
    
    return get_base_template(f"Commande prête N°{order_number}", content)


async def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send an email using SMTP"""
    if not SMTP_PASSWORD:
        logger.warning("SMTP_PASSWORD not configured, email not sent")
        # In demo mode, just log the email
        logger.info(f"[DEMO] Email would be sent to {to_email}: {subject}")
        return True
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['To'] = to_email
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Use SSL connection
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        return False


async def send_order_confirmation(order: Dict) -> bool:
    """Send order confirmation email"""
    email = order.get('customer_email')
    if not email:
        return False
    
    subject = f"✨ Commande confirmée N°{order.get('order_number', '')} — Kyrios Salon"
    html_content = generate_order_confirmation_email(order)
    return await send_email(email, subject, html_content)


async def send_deposit_received(order: Dict) -> bool:
    """Send deposit received email"""
    email = order.get('customer_email')
    if not email:
        return False
    
    subject = f"✅ Acompte reçu — Commande en préparation"
    html_content = generate_deposit_received_email(order)
    return await send_email(email, subject, html_content)


async def send_order_ready(order: Dict) -> bool:
    """Send order ready email"""
    email = order.get('customer_email')
    if not email:
        return False
    
    subject = f"🎉 Votre commande est prête ! — Kyrios Salon"
    html_content = generate_order_ready_email(order)
    return await send_email(email, subject, html_content)
