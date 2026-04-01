"""
CMS Routes for Kyrios Salon Admin Dashboard
- Advanced Product Management
- Site Content Management
- Announcements/Promos/Events
- Media Library
- Notification Logs
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timezone
import uuid
import os
import logging
import base64
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create router
cms_router = APIRouter(prefix="/api")


# ============== PRODUCT MODELS ==============

class PriceVariation(BaseModel):
    size: str  # S, M, L, XL
    price: float
    available: bool = True


class ProductAdvanced(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str  # Lisse, Ondulé, Bouclé, Afro, Bulk for Braids, Raw Hair
    short_description: str
    long_description: Optional[str] = None
    care_instructions: Optional[str] = None
    images: List[str] = []  # URLs of product images (1-5)
    prices_by_size: List[PriceVariation] = []
    has_color_supplement: bool = False
    color_supplement_amount: float = 20.0
    product_type: str = "extension"  # "extension" or "perruque"
    status: str = "active"  # "active" or "inactive"
    badge: Optional[str] = None  # "nouveau", "bestseller", "promo", None
    lace_types: List[str] = []
    is_raw_hair: bool = False
    is_bulk: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProductCreate(BaseModel):
    name: str
    category: str
    short_description: str
    long_description: Optional[str] = None
    care_instructions: Optional[str] = None
    images: List[str] = []
    prices_by_size: List[PriceVariation] = []
    has_color_supplement: bool = False
    color_supplement_amount: float = 20.0
    product_type: str = "extension"
    status: str = "active"
    badge: Optional[str] = None
    lace_types: List[str] = []
    is_raw_hair: bool = False
    is_bulk: bool = False


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    care_instructions: Optional[str] = None
    images: Optional[List[str]] = None
    prices_by_size: Optional[List[PriceVariation]] = None
    has_color_supplement: Optional[bool] = None
    color_supplement_amount: Optional[float] = None
    product_type: Optional[str] = None
    status: Optional[str] = None
    badge: Optional[str] = None
    lace_types: Optional[List[str]] = None
    is_raw_hair: Optional[bool] = None
    is_bulk: Optional[bool] = None


# ============== SITE CONTENT MODELS ==============

class HeroContent(BaseModel):
    title: str = "Lyrias'Hair"
    subtitle: str = "Extensions & Perruques de Luxe"
    background_image: Optional[str] = None  # URL de l'image héros (1920x1080 recommandé)
    cta_button_1_text: str = "Découvrir la Collection"
    cta_button_1_link: str = "/boutique"
    cta_button_2_text: str = "Réserver au Salon"
    cta_button_2_link: str = "#reservation"


class SocialLinks(BaseModel):
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None


class SalonInfo(BaseModel):
    address: str = "Rue du Pont-de-Perrette 8, 1700 Fribourg"
    phone: str = "+41 78 848 08 67"
    email: str = "clients@kyrios-salon.ch"
    salon_image: Optional[str] = None  # URL de l'image du salon (1920x800 recommandé)
    social_links: SocialLinks = Field(default_factory=SocialLinks)
    hours: Dict[str, str] = {
        "monday": "Fermé",
        "tuesday": "Fermé",
        "wednesday": "7h30 - 18h30",
        "thursday": "7h30 - 18h30",
        "friday": "7h30 - 18h30",
        "saturday": "7h30 - 18h30",
        "sunday": "Fermé"
    }


class Testimonial(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    client_city: Optional[str] = None
    text: str
    rating: int = 5  # 1-5 stars
    is_visible: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SiteContent(BaseModel):
    id: str = "site_content_main"
    hero: HeroContent = Field(default_factory=HeroContent)
    salon_info: SalonInfo = Field(default_factory=SalonInfo)
    testimonials: List[Testimonial] = []
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============== ANNOUNCEMENT MODELS ==============

class Announcement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # "promo", "annonce", "evenement"
    title: str
    description: str
    image_url: Optional[str] = None
    display_formats: List[str] = []  # ["banner", "popup", "homepage"]
    start_date: str  # ISO date string
    end_date: str  # ISO date string
    cta_text: Optional[str] = None
    cta_link: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnnouncementCreate(BaseModel):
    type: str
    title: str
    description: str
    image_url: Optional[str] = None
    display_formats: List[str] = []
    start_date: str
    end_date: str
    cta_text: Optional[str] = None
    cta_link: Optional[str] = None
    is_active: bool = True


# ============== MEDIA LIBRARY MODELS ==============

class MediaItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    url: str
    file_type: str  # "image/jpeg", "image/png", "image/webp"
    file_size: int  # bytes
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============== NOTIFICATION LOG MODELS ==============

class NotificationLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # "email", "whatsapp"
    recipient: str
    subject: Optional[str] = None  # For emails
    message: str
    status: str = "sent"  # "sent", "failed", "pending"
    related_to: Optional[str] = None  # order_id or appointment_id
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============== PRODUCT ROUTES ==============

@cms_router.get("/admin/products-advanced")
async def get_all_products_advanced():
    """Get all products with advanced fields"""
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    return products


@cms_router.post("/admin/products")
async def create_product(product: ProductCreate):
    """Create a new product"""
    product_doc = ProductAdvanced(
        **product.model_dump()
    )
    
    product_dict = product_doc.model_dump()
    product_dict['created_at'] = product_dict['created_at'].isoformat()
    product_dict['updated_at'] = product_dict['updated_at'].isoformat()
    
    # Also add legacy fields for compatibility
    product_dict['image_url'] = product_dict['images'][0] if product_dict['images'] else ''
    product_dict['description'] = product_dict['short_description']
    
    await db.products.insert_one(product_dict)
    
    return {"id": product_doc.id, "message": "Produit créé avec succès"}


@cms_router.put("/admin/products/{product_id}")
async def update_product(product_id: str, product: ProductUpdate):
    """Update an existing product"""
    update_data = {k: v for k, v in product.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Update legacy fields for compatibility
    if 'images' in update_data and update_data['images']:
        update_data['image_url'] = update_data['images'][0]
    if 'short_description' in update_data:
        update_data['description'] = update_data['short_description']
    
    result = await db.products.update_one(
        {"id": product_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    return {"message": "Produit mis à jour avec succès"}


@cms_router.delete("/admin/products/{product_id}")
async def delete_product(product_id: str):
    """Delete a product"""
    result = await db.products.delete_one({"id": product_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    return {"message": "Produit supprimé avec succès"}


# ============== SITE CONTENT ROUTES ==============

@cms_router.get("/site-content")
async def get_site_content():
    """Get site content (public)"""
    content = await db.site_content.find_one({"id": "site_content_main"}, {"_id": 0})
    
    if not content:
        # Initialize with defaults
        default_content = SiteContent()
        content_dict = default_content.model_dump()
        content_dict['updated_at'] = content_dict['updated_at'].isoformat()
        await db.site_content.insert_one(content_dict)
        return default_content.model_dump()
    
    # Normalize salon_info to include social_links (backwards compatibility)
    if 'salon_info' in content:
        salon_info = content['salon_info']
        if 'social_links' not in salon_info:
            # Migrate old instagram field to new structure
            salon_info['social_links'] = {
                'instagram': salon_info.get('instagram'),
                'facebook': None,
                'tiktok': None,
                'youtube': None
            }
        if 'salon_image' not in salon_info:
            salon_info['salon_image'] = None
    
    return content


@cms_router.put("/admin/site-content/hero")
async def update_hero_content(hero: HeroContent):
    """Update hero section content"""
    await db.site_content.update_one(
        {"id": "site_content_main"},
        {
            "$set": {
                "hero": hero.model_dump(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    return {"message": "Section Hero mise à jour"}


@cms_router.put("/admin/site-content/salon-info")
async def update_salon_info(salon_info: SalonInfo):
    """Update salon info content"""
    await db.site_content.update_one(
        {"id": "site_content_main"},
        {
            "$set": {
                "salon_info": salon_info.model_dump(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    return {"message": "Informations salon mises à jour"}


# ============== TESTIMONIALS ROUTES ==============

@cms_router.get("/testimonials")
async def get_testimonials(visible_only: bool = True):
    """Get testimonials (public)"""
    content = await db.site_content.find_one({"id": "site_content_main"}, {"_id": 0})
    
    if not content or 'testimonials' not in content:
        return []
    
    testimonials = content.get('testimonials', [])
    
    if visible_only:
        testimonials = [t for t in testimonials if t.get('is_visible', True)]
    
    return testimonials


@cms_router.post("/admin/testimonials")
async def create_testimonial(testimonial: Testimonial):
    """Create a new testimonial"""
    testimonial_dict = testimonial.model_dump()
    testimonial_dict['created_at'] = testimonial_dict['created_at'].isoformat()
    
    await db.site_content.update_one(
        {"id": "site_content_main"},
        {
            "$push": {"testimonials": testimonial_dict},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    return {"id": testimonial.id, "message": "Témoignage créé avec succès"}


@cms_router.put("/admin/testimonials/{testimonial_id}")
async def update_testimonial(testimonial_id: str, testimonial: Testimonial):
    """Update a testimonial"""
    content = await db.site_content.find_one({"id": "site_content_main"}, {"_id": 0})
    
    if not content or 'testimonials' not in content:
        raise HTTPException(status_code=404, detail="Témoignage non trouvé")
    
    testimonials = content.get('testimonials', [])
    updated = False
    
    for i, t in enumerate(testimonials):
        if t.get('id') == testimonial_id:
            testimonial_dict = testimonial.model_dump()
            testimonial_dict['id'] = testimonial_id
            if isinstance(testimonial_dict.get('created_at'), datetime):
                testimonial_dict['created_at'] = testimonial_dict['created_at'].isoformat()
            testimonials[i] = testimonial_dict
            updated = True
            break
    
    if not updated:
        raise HTTPException(status_code=404, detail="Témoignage non trouvé")
    
    await db.site_content.update_one(
        {"id": "site_content_main"},
        {
            "$set": {
                "testimonials": testimonials,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Témoignage mis à jour"}


@cms_router.delete("/admin/testimonials/{testimonial_id}")
async def delete_testimonial(testimonial_id: str):
    """Delete a testimonial"""
    await db.site_content.update_one(
        {"id": "site_content_main"},
        {
            "$pull": {"testimonials": {"id": testimonial_id}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Témoignage supprimé"}


# ============== ANNOUNCEMENTS ROUTES ==============

@cms_router.get("/announcements")
async def get_active_announcements():
    """Get active announcements (public)"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    announcements = await db.announcements.find({
        "is_active": True,
        "start_date": {"$lte": now},
        "end_date": {"$gte": now}
    }, {"_id": 0}).to_list(100)
    
    return announcements


@cms_router.get("/admin/announcements")
async def get_all_announcements():
    """Get all announcements (admin)"""
    announcements = await db.announcements.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Mark expired announcements
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for a in announcements:
        a['is_expired'] = a.get('end_date', '') < now
    
    return announcements


@cms_router.post("/admin/announcements")
async def create_announcement(announcement: AnnouncementCreate):
    """Create a new announcement"""
    announcement_doc = Announcement(**announcement.model_dump())
    
    announcement_dict = announcement_doc.model_dump()
    announcement_dict['created_at'] = announcement_dict['created_at'].isoformat()
    
    await db.announcements.insert_one(announcement_dict)
    
    return {"id": announcement_doc.id, "message": "Annonce créée avec succès"}


@cms_router.put("/admin/announcements/{announcement_id}")
async def update_announcement(announcement_id: str, announcement: AnnouncementCreate):
    """Update an announcement"""
    update_data = announcement.model_dump()
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.announcements.update_one(
        {"id": announcement_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Annonce non trouvée")
    
    return {"message": "Annonce mise à jour"}


@cms_router.delete("/admin/announcements/{announcement_id}")
async def delete_announcement(announcement_id: str):
    """Delete an announcement"""
    result = await db.announcements.delete_one({"id": announcement_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Annonce non trouvée")
    
    return {"message": "Annonce supprimée"}


# ============== MEDIA LIBRARY ROUTES ==============

@cms_router.get("/admin/media")
async def get_media_library():
    """Get all media items"""
    media = await db.media_library.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return media


@cms_router.post("/admin/media/upload")
async def upload_media(file_data: str = Form(...), filename: str = Form(...)):
    """
    Upload a media file (base64 encoded)
    In production, this would upload to cloud storage
    For demo, we store base64 and generate a data URL
    """
    try:
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']
        
        # Parse base64 data
        if ',' in file_data:
            header, data = file_data.split(',', 1)
            file_type = header.split(';')[0].split(':')[1] if ':' in header else 'image/jpeg'
        else:
            data = file_data
            file_type = 'image/jpeg'
        
        if file_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Type de fichier non autorisé")
        
        # Calculate file size
        file_size = len(base64.b64decode(data))
        
        # Max 5MB
        if file_size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 5 MB)")
        
        # Create media item
        media_item = MediaItem(
            filename=filename,
            url=file_data,  # Store as data URL for demo
            file_type=file_type,
            file_size=file_size
        )
        
        media_dict = media_item.model_dump()
        media_dict['created_at'] = media_dict['created_at'].isoformat()
        
        await db.media_library.insert_one(media_dict)
        
        return {
            "id": media_item.id,
            "url": media_item.url,
            "message": "Image uploadée avec succès"
        }
        
    except Exception as e:
        logger.error(f"Media upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@cms_router.delete("/admin/media/{media_id}")
async def delete_media(media_id: str):
    """Delete a media item"""
    result = await db.media_library.delete_one({"id": media_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Média non trouvé")
    
    return {"message": "Média supprimé"}


# ============== NOTIFICATION LOG ROUTES ==============

@cms_router.get("/admin/notification-logs")
async def get_notification_logs(limit: int = 50):
    """Get notification logs for admin dashboard"""
    logs = await db.notification_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return logs


@cms_router.post("/admin/notification-logs")
async def create_notification_log(log: NotificationLog):
    """Create a notification log entry (used by email/whatsapp services)"""
    log_dict = log.model_dump()
    log_dict['created_at'] = log_dict['created_at'].isoformat()
    
    await db.notification_logs.insert_one(log_dict)
    
    return {"id": log.id}


# Helper function to log notifications (used by email and whatsapp services)
async def log_notification(
    notification_type: str,
    recipient: str,
    message: str,
    subject: str = None,
    related_to: str = None,
    status: str = "sent"
):
    """Log a notification to the database"""
    log = NotificationLog(
        type=notification_type,
        recipient=recipient,
        subject=subject,
        message=message,
        status=status,
        related_to=related_to
    )
    
    log_dict = log.model_dump()
    log_dict['created_at'] = log_dict['created_at'].isoformat()
    
    await db.notification_logs.insert_one(log_dict)
    
    return log.id
