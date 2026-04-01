from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from bson import ObjectId
import stripe

# Import email and whatsapp services
from email_service import (
    send_order_confirmation, send_deposit_received, send_order_ready
)
from whatsapp_service import notify_order_ready, notify_order_cancelled

# Import enhanced services
from email_service_enhanced import (
    send_order_confirmation_email, send_deposit_received_email, 
    send_order_ready_email, send_appointment_confirmation_email,
    send_appointment_reminder_email
)
from email_service import send_salon_notification
from whatsapp_service_enhanced import (
    notify_new_order, notify_new_appointment, notify_appointment_reminder
)

# Import booking routes
from booking_routes import booking_router

# Import CMS routes
from cms_routes import cms_router

# Import reminder scheduler
from reminder_scheduler import start_scheduler, stop_scheduler, trigger_reminder_check, send_test_reminder

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe API Key
stripe_api_key = os.environ.get('STRIPE_API_KEY', 'sk_test_emergent')
stripe.api_key = stripe_api_key

# Create the main app
app = FastAPI(title="Kyrios Salon / Lyrias'Hair API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== HEALTH CHECK ==============

@api_router.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy", "service": "kyrios-salon-backend"}

# ============== MODELS ==============

class PriceBySize(BaseModel):
    size: str
    price: float

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str  # Lisse, Ondulé, Bouclé, Afro, Raw Hair, Bulk for Braids
    subcategory: Optional[str] = None
    description: str
    care_instructions: str
    image_url: str
    prices_by_size: List[PriceBySize]
    lace_types: List[str]
    is_raw_hair: bool = False
    is_bulk: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductResponse(BaseModel):
    id: str
    name: str
    category: str
    subcategory: Optional[str] = None
    description: str
    care_instructions: str
    image_url: str
    prices_by_size: List[PriceBySize]
    lace_types: List[str]
    is_raw_hair: bool
    is_bulk: bool

class CartItem(BaseModel):
    product_id: str
    product_name: str
    category: str
    size: str
    lace_type: str
    coloration: bool  # True = +20 CHF
    delivery_method: str  # "salon" or "postal"
    comment: Optional[str] = None
    quantity: int = 1
    unit_price: float
    total_price: float

class CartItemCreate(BaseModel):
    product_id: str
    size: str
    lace_type: str
    coloration: bool = False
    delivery_method: str = "salon"
    comment: Optional[str] = None
    quantity: int = 1

class Cart(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    items: List[CartItem] = []
    subtotal: float = 0.0
    coloration_supplement: float = 0.0
    total: float = 0.0
    requires_deposit: bool = False
    deposit_amount: float = 0.0
    remaining_amount: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str
    customer_email: str
    customer_name: str
    customer_phone: str
    items: List[CartItem]
    subtotal: float
    coloration_supplement: float
    total: float
    payment_type: str  # "full" or "deposit"
    amount_paid: float
    remaining_to_pay: float
    status: str = "pending"  # pending, paid, processing, completed, cancelled
    stripe_session_id: Optional[str] = None
    delivery_method: str
    delivery_address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderCreate(BaseModel):
    customer_email: str
    customer_name: str
    customer_phone: str
    delivery_address: Optional[str] = None
    origin_url: str

class PaymentTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    session_id: str
    amount: float
    currency: str = "chf"
    payment_status: str = "initiated"  # initiated, pending, paid, failed, expired
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============== WIGS (PERRUQUES) MODELS ==============

class Wig(BaseModel):
    """Wig product - no sizes, no colors, unique product"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    image_url: str
    price: float
    is_available: bool = True
    order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WigCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: str
    price: float
    is_available: bool = True
    order: int = 0

class WigUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    is_available: Optional[bool] = None
    order: Optional[int] = None

# ============== PRODUCT ROUTES ==============

@api_router.get("/")
async def root():
    return {"message": "Bienvenue sur l'API Kyrios Salon / Lyrias'Hair"}

@api_router.get("/products", response_model=List[ProductResponse])
async def get_products(category: Optional[str] = None):
    query = {}
    if category:
        query["category"] = category
    products = await db.products.find(query, {"_id": 0}).to_list(1000)
    return products

@api_router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return product

@api_router.get("/categories")
async def get_categories():
    categories = await db.products.distinct("category")
    return {"categories": categories}


# ============== WIGS (PERRUQUES) ROUTES ==============

@api_router.get("/wigs")
async def get_wigs():
    """Get all available wigs"""
    wigs = await db.wigs.find({"is_available": True}, {"_id": 0}).sort("order", 1).to_list(100)
    return wigs

@api_router.get("/wigs/all")
async def get_all_wigs():
    """Get all wigs (admin)"""
    wigs = await db.wigs.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    return wigs

@api_router.get("/wigs/{wig_id}")
async def get_wig(wig_id: str):
    """Get a single wig by ID"""
    wig = await db.wigs.find_one({"id": wig_id}, {"_id": 0})
    if not wig:
        raise HTTPException(status_code=404, detail="Perruque non trouvée")
    return wig

@api_router.post("/admin/wigs")
async def create_wig(wig: WigCreate):
    """Create a new wig (admin)"""
    new_wig = Wig(**wig.model_dump())
    wig_dict = new_wig.model_dump()
    wig_dict['created_at'] = wig_dict['created_at'].isoformat()
    await db.wigs.insert_one(wig_dict)
    return {"message": "Perruque créée", "id": new_wig.id}

@api_router.put("/admin/wigs/{wig_id}")
async def update_wig(wig_id: str, wig: WigUpdate):
    """Update a wig (admin)"""
    update_data = {k: v for k, v in wig.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
    
    result = await db.wigs.update_one({"id": wig_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Perruque non trouvée")
    return {"message": "Perruque mise à jour"}

@api_router.delete("/admin/wigs/{wig_id}")
async def delete_wig(wig_id: str):
    """Delete a wig (admin)"""
    result = await db.wigs.delete_one({"id": wig_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Perruque non trouvée")
    return {"message": "Perruque supprimée"}


# ============== SHOP PRODUCTS (PRODUITS CAPILLAIRES) MODELS ==============

class ShopProduct(BaseModel):
    """Shop product - hair care products (shampoos, creams, oils, etc.)"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    category: Optional[str] = None  # Shampoing, Crème, Huile, Sérum, Sèche-cheveux, etc.
    image_url: str
    price: float
    is_available: bool = True
    order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ShopProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    image_url: str
    price: float
    is_available: bool = True
    order: int = 0

class ShopProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    is_available: Optional[bool] = None
    order: Optional[int] = None


# ============== SHOP PRODUCTS (PRODUITS CAPILLAIRES) ROUTES ==============

@api_router.get("/shop-products")
async def get_shop_products():
    """Get all available shop products"""
    products = await db.shop_products.find({"is_available": True}, {"_id": 0}).sort("order", 1).to_list(100)
    return products

@api_router.get("/shop-products/all")
async def get_all_shop_products():
    """Get all shop products (admin)"""
    products = await db.shop_products.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    return products

@api_router.get("/shop-products/{product_id}")
async def get_shop_product(product_id: str):
    """Get a single shop product by ID"""
    product = await db.shop_products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return product

@api_router.post("/admin/shop-products")
async def create_shop_product(product: ShopProductCreate):
    """Create a new shop product (admin)"""
    new_product = ShopProduct(**product.model_dump())
    product_dict = new_product.model_dump()
    product_dict['created_at'] = product_dict['created_at'].isoformat()
    await db.shop_products.insert_one(product_dict)
    return {"message": "Produit créé", "id": new_product.id}

@api_router.put("/admin/shop-products/{product_id}")
async def update_shop_product(product_id: str, product: ShopProductUpdate):
    """Update a shop product (admin)"""
    update_data = {k: v for k, v in product.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
    
    result = await db.shop_products.update_one({"id": product_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return {"message": "Produit mis à jour"}

@api_router.delete("/admin/shop-products/{product_id}")
async def delete_shop_product(product_id: str):
    """Delete a shop product (admin)"""
    result = await db.shop_products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return {"message": "Produit supprimé"}


# ============== CART ROUTES ==============

def calculate_cart_totals(items: List[CartItem]) -> Dict:
    subtotal = sum(item.unit_price * item.quantity for item in items)
    coloration_supplement = sum(20.0 * item.quantity for item in items if item.coloration)
    total = subtotal + coloration_supplement
    
    requires_deposit = total >= 150.0
    deposit_amount = 50.0 if requires_deposit else 0.0
    remaining_amount = total - deposit_amount if requires_deposit else 0.0
    
    return {
        "subtotal": subtotal,
        "coloration_supplement": coloration_supplement,
        "total": total,
        "requires_deposit": requires_deposit,
        "deposit_amount": deposit_amount,
        "remaining_amount": remaining_amount
    }

@api_router.get("/cart/{session_id}")
async def get_cart(session_id: str):
    cart = await db.carts.find_one({"session_id": session_id}, {"_id": 0})
    if not cart:
        # Create new cart
        new_cart = Cart(session_id=session_id)
        cart_dict = new_cart.model_dump()
        cart_dict['created_at'] = cart_dict['created_at'].isoformat()
        cart_dict['updated_at'] = cart_dict['updated_at'].isoformat()
        await db.carts.insert_one(cart_dict)
        return new_cart.model_dump()
    
    # Convert ISO strings back to datetime for response
    if isinstance(cart.get('created_at'), str):
        cart['created_at'] = datetime.fromisoformat(cart['created_at'])
    if isinstance(cart.get('updated_at'), str):
        cart['updated_at'] = datetime.fromisoformat(cart['updated_at'])
    
    return cart

@api_router.post("/cart/{session_id}/add")
async def add_to_cart(session_id: str, item: CartItemCreate):
    # Get product
    product = await db.products.find_one({"id": item.product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    if product.get("is_raw_hair"):
        raise HTTPException(status_code=400, detail="Les produits Raw Hair ne peuvent pas être ajoutés au panier. Veuillez demander un devis via WhatsApp.")
    
    # Find price for size
    price = None
    for p in product["prices_by_size"]:
        if p["size"] == item.size:
            price = p["price"]
            break
    
    if price is None:
        raise HTTPException(status_code=400, detail="Taille non disponible")
    
    # Create cart item
    cart_item = CartItem(
        product_id=item.product_id,
        product_name=product["name"],
        category=product["category"],
        size=item.size,
        lace_type=item.lace_type,
        coloration=item.coloration,
        delivery_method=item.delivery_method,
        comment=item.comment,
        quantity=item.quantity,
        unit_price=price,
        total_price=price + (20.0 if item.coloration else 0.0)
    )
    
    # Get or create cart
    cart = await db.carts.find_one({"session_id": session_id})
    
    if cart:
        items = [CartItem(**i) for i in cart.get("items", [])]
        items.append(cart_item)
        totals = calculate_cart_totals(items)
        
        await db.carts.update_one(
            {"session_id": session_id},
            {
                "$push": {"items": cart_item.model_dump()},
                "$set": {
                    **totals,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
    else:
        items = [cart_item]
        totals = calculate_cart_totals(items)
        new_cart = Cart(
            session_id=session_id,
            items=items,
            **totals
        )
        cart_dict = new_cart.model_dump()
        cart_dict['created_at'] = cart_dict['created_at'].isoformat()
        cart_dict['updated_at'] = cart_dict['updated_at'].isoformat()
        await db.carts.insert_one(cart_dict)
    
    # Return updated cart
    updated_cart = await db.carts.find_one({"session_id": session_id}, {"_id": 0})
    return updated_cart

@api_router.delete("/cart/{session_id}/item/{item_index}")
async def remove_from_cart(session_id: str, item_index: int):
    cart = await db.carts.find_one({"session_id": session_id})
    if not cart:
        raise HTTPException(status_code=404, detail="Panier non trouvé")
    
    items = cart.get("items", [])
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(status_code=400, detail="Index d'article invalide")
    
    items.pop(item_index)
    cart_items = [CartItem(**i) for i in items]
    totals = calculate_cart_totals(cart_items)
    
    await db.carts.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "items": items,
                **totals,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    updated_cart = await db.carts.find_one({"session_id": session_id}, {"_id": 0})
    return updated_cart

@api_router.delete("/cart/{session_id}")
async def clear_cart(session_id: str):
    await db.carts.delete_one({"session_id": session_id})
    return {"message": "Panier vidé"}

# ============== ORDER & CHECKOUT ROUTES ==============

def generate_order_number():
    now = datetime.now(timezone.utc)
    return f"KYR-{now.strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

@api_router.post("/checkout")
async def create_checkout(session_id: str, order_data: OrderCreate, request: Request):
    # Get cart
    cart = await db.carts.find_one({"session_id": session_id}, {"_id": 0})
    if not cart or not cart.get("items"):
        raise HTTPException(status_code=400, detail="Panier vide")
    
    # Determine delivery method from items
    delivery_methods = set(item["delivery_method"] for item in cart["items"])
    delivery_method = "postal" if "postal" in delivery_methods else "salon"
    
    # Calculate payment
    total = cart["total"]
    requires_deposit = total >= 150.0
    amount_to_pay = 50.0 if requires_deposit else total
    remaining = total - amount_to_pay if requires_deposit else 0.0
    
    # Create order
    order = Order(
        order_number=generate_order_number(),
        customer_email=order_data.customer_email,
        customer_name=order_data.customer_name,
        customer_phone=order_data.customer_phone,
        items=[CartItem(**item) for item in cart["items"]],
        subtotal=cart["subtotal"],
        coloration_supplement=cart["coloration_supplement"],
        total=total,
        payment_type="deposit" if requires_deposit else "full",
        amount_paid=0.0,
        remaining_to_pay=total,
        delivery_method=delivery_method,
        delivery_address=order_data.delivery_address if delivery_method == "postal" else None
    )
    
    order_dict = order.model_dump()
    order_dict['created_at'] = order_dict['created_at'].isoformat()
    await db.orders.insert_one(order_dict)
    
    # Create Stripe checkout session
    origin_url = order_data.origin_url.rstrip('/')
    success_url = f"{origin_url}/order-confirmation?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/cart"
    
    metadata = {
        "order_id": order.id,
        "order_number": order.order_number,
        "customer_email": order_data.customer_email,
        "payment_type": order.payment_type
    }
    
    try:
        # Create Stripe checkout session using standard stripe library
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "chf",
                    "product_data": {
                        "name": f"Commande {order.order_number}" + (" (Acompte)" if requires_deposit else ""),
                    },
                    "unit_amount": int(amount_to_pay * 100),  # Stripe uses cents
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            customer_email=order_data.customer_email,
        )
        
        # Update order with stripe session
        await db.orders.update_one(
            {"id": order.id},
            {"$set": {"stripe_session_id": checkout_session.id}}
        )
        
        # Create payment transaction record
        payment_transaction = PaymentTransaction(
            order_id=order.id,
            session_id=checkout_session.id,
            amount=float(amount_to_pay),
            currency="chf",
            payment_status="initiated",
            metadata=metadata
        )
        trans_dict = payment_transaction.model_dump()
        trans_dict['created_at'] = trans_dict['created_at'].isoformat()
        trans_dict['updated_at'] = trans_dict['updated_at'].isoformat()
        await db.payment_transactions.insert_one(trans_dict)
        
        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id,
            "order_id": order.id,
            "order_number": order.order_number,
            "amount_to_pay": amount_to_pay,
            "total": total,
            "payment_type": order.payment_type,
            "remaining_after_payment": remaining
        }
        
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du paiement: {str(e)}")

@api_router.get("/checkout/status/{checkout_session_id}")
async def get_checkout_status(checkout_session_id: str, request: Request):
    try:
        # Get checkout session status using standard stripe library
        session = stripe.checkout.Session.retrieve(checkout_session_id)
        
        payment_status = "paid" if session.payment_status == "paid" else "pending"
        
        # Find the payment transaction
        transaction = await db.payment_transactions.find_one({"session_id": checkout_session_id})
        
        if transaction and transaction.get("payment_status") != payment_status:
            # Update transaction status
            await db.payment_transactions.update_one(
                {"session_id": checkout_session_id},
                {
                    "$set": {
                        "payment_status": payment_status,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            # If paid, update order
            if payment_status == "paid":
                order_id = session.metadata.get("order_id") if session.metadata else None
                if order_id:
                    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
                    if order and order.get("status") not in ["paid", "deposit_paid"]:
                        amount_paid = session.amount_total / 100  # Stripe returns cents
                        remaining = order["total"] - amount_paid
                        
                        new_status = "paid" if remaining <= 0 else "deposit_paid"
                        
                        await db.orders.update_one(
                            {"id": order_id},
                            {
                                "$set": {
                                    "status": new_status,
                                    "amount_paid": amount_paid,
                                    "remaining_to_pay": max(0, remaining)
                                }
                            }
                        )
                        
                        # Send email notifications
                        try:
                            # Update order dict with new values for email
                            order['amount_paid'] = amount_paid
                            order['remaining_to_pay'] = max(0, remaining)
                            
                            # Send order confirmation email
                            await send_order_confirmation(order)
                            
                            # If deposit paid, also send deposit confirmation
                            if new_status == "deposit_paid":
                                await send_deposit_received(order)
                            
                            logger.info(f"Order confirmation emails sent for {order_id}")
                        except Exception as e:
                            logger.error(f"Error sending order emails: {e}")
        
        return {
            "status": session.status,
            "payment_status": payment_status,
            "amount_total": session.amount_total,
            "currency": session.currency,
            "metadata": dict(session.metadata) if session.metadata else {}
        }
        
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@api_router.get("/order/{order_id}")
async def get_order(order_id: str):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return order

@api_router.get("/order/by-session/{session_id}")
async def get_order_by_stripe_session(session_id: str):
    order = await db.orders.find_one({"stripe_session_id": session_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return order

# ============== ADMIN ROUTES ==============

class StatusUpdate(BaseModel):
    status: str

@api_router.get("/admin/orders")
async def get_all_orders():
    orders = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return orders

@api_router.get("/admin/orders/{order_id}")
async def get_order_admin(order_id: str):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return order

@api_router.patch("/admin/orders/{order_id}/status")
async def update_order_status(order_id: str, status_update: StatusUpdate):
    valid_statuses = ["pending", "processing", "ready", "delivered", "cancelled", "deposit_paid", "paid"]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Statut invalide")
    
    # Get current order for notification
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    old_status = order.get('status')
    
    result = await db.orders.update_one(
        {"id": order_id},
        {"$set": {"status": status_update.status}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    # Send notifications based on status change
    try:
        if status_update.status == "ready" and old_status != "ready":
            # Send "Order Ready" email and WhatsApp
            await send_order_ready(order)
            await notify_order_ready(order)
            logger.info(f"Order ready notifications sent for {order_id}")
        
        elif status_update.status == "cancelled" and old_status != "cancelled":
            # Send cancellation WhatsApp
            await notify_order_cancelled(order)
            logger.info(f"Order cancelled notification sent for {order_id}")
    except Exception as e:
        logger.error(f"Error sending notifications: {e}")
    
    return {"message": "Statut mis à jour", "status": status_update.status}

@api_router.get("/admin/stats")
async def get_admin_stats():
    from datetime import timedelta
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get all orders
    all_orders = await db.orders.find({}, {"_id": 0}).to_list(1000)
    
    # Calculate stats
    today_orders = sum(1 for o in all_orders if o.get('created_at') and datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')) >= today_start)
    week_orders = sum(1 for o in all_orders if o.get('created_at') and datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')) >= week_ago)
    
    month_revenue = sum(
        o.get('amount_paid', 0) 
        for o in all_orders 
        if o.get('status') != 'cancelled' and o.get('created_at') and datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')) >= month_start
    )
    
    pending_deposits = sum(1 for o in all_orders if o.get('status') == 'deposit_paid')
    
    total_due = sum(
        o.get('remaining_to_pay', 0) 
        for o in all_orders 
        if o.get('remaining_to_pay', 0) > 0 and o.get('status') != 'cancelled'
    )
    
    return {
        "today_orders": today_orders,
        "week_orders": week_orders,
        "month_revenue": month_revenue,
        "pending_deposits": pending_deposits,
        "total_due": total_due
    }

# ============== WEBHOOK ==============

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    try:
        body = await request.body()
        signature = request.headers.get("Stripe-Signature")
        
        # For now, parse the event without signature verification
        # In production, add STRIPE_WEBHOOK_SECRET and verify
        import json
        event_data = json.loads(body)
        event_type = event_data.get("type", "")
        
        logger.info(f"Webhook received: {event_type}")
        
        if event_type == "checkout.session.completed":
            session = event_data.get("data", {}).get("object", {})
            metadata = session.get("metadata", {})
            payment_status = session.get("payment_status", "")
            
            if payment_status == "paid":
                # Handle order payment
                order_id = metadata.get("order_id")
                if order_id:
                    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
                    if order:
                        await db.orders.update_one(
                            {"id": order_id},
                            {"$set": {"status": "processing"}}
                        )
                        
                        # Send enhanced notifications
                        try:
                            await send_order_confirmation_email(order)
                            await send_deposit_received_email(order)
                            await notify_new_order(order)
                        except Exception as notif_error:
                            logger.error(f"Notification error for order: {notif_error}")
                
                # Handle booking deposit payment
                appointment_id = metadata.get("appointment_id")
                if appointment_id:
                    appointment = await db.appointments.find_one({"id": appointment_id}, {"_id": 0})
                    if appointment and not appointment.get("deposit_paid"):
                        await db.appointments.update_one(
                            {"id": appointment_id},
                            {"$set": {
                                "deposit_paid": True,
                                "status": "confirmed"
                            }}
                        )
                        logger.info(f"Booking {appointment_id} confirmed after payment")
                        
                        # Send appointment notifications
                        try:
                            # Refresh appointment data
                            updated_appt = await db.appointments.find_one({"id": appointment_id}, {"_id": 0})
                            if updated_appt:
                                # Email to customer
                                await send_appointment_confirmation_email(updated_appt)
                                # Email to salon
                                await send_salon_notification(updated_appt)
                                # WhatsApp notification
                                await notify_new_appointment(updated_appt)
                        except Exception as notif_error:
                            logger.error(f"Notification error for appointment: {notif_error}")
        
        return {"received": True}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"received": False, "error": str(e)}


# ============== SCHEDULER API ROUTES ==============

@api_router.post("/admin/reminders/trigger-check")
async def trigger_reminder_check_api():
    """Manually trigger the reminder check (admin only)"""
    try:
        await trigger_reminder_check()
        return {"success": True, "message": "Reminder check triggered"}
    except Exception as e:
        logger.error(f"Manual reminder trigger error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/admin/reminders/test/{appointment_id}")
async def test_reminder_api(appointment_id: str):
    """Send a test reminder for a specific appointment (admin only)"""
    try:
        result = await send_test_reminder(appointment_id)
        return result
    except Exception as e:
        logger.error(f"Test reminder error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/scheduler-status")
async def get_scheduler_status():
    """Get the scheduler status"""
    from reminder_scheduler import scheduler
    
    if scheduler is None:
        return {"status": "not_started", "running": False}
    
    return {
        "status": "running" if scheduler.running else "stopped",
        "running": scheduler.running,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None
            }
            for job in scheduler.get_jobs()
        ]
    }


# Include the router in the main app
app.include_router(api_router)

# Include booking routes
app.include_router(booking_router)

# Include CMS routes
app.include_router(cms_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== SCHEDULER EVENTS ==============

@app.on_event("startup")
async def start_reminder_scheduler():
    """Start the reminder scheduler on app startup"""
    try:
        start_scheduler()
        logger.info("Reminder scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start reminder scheduler: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    """Cleanup on shutdown"""
    try:
        stop_scheduler()
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
    client.close()

# Download endpoint for frontend zip
from fastapi.responses import FileResponse
import os

@app.get("/download/frontend-v9")
async def download_frontend():
    file_path = os.path.join(os.path.dirname(__file__), "kyrios-salon-frontend-v9.zip")
    return FileResponse(
        path=file_path,
        filename="kyrios-salon-frontend-v9.zip",
        media_type="application/zip"
    )

@app.get("/api/download/frontend-v13")
async def download_frontend_v13():
    file_path = "/app/kyrios-salon-frontend-v13.zip"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Fichier non trouvé")
    return FileResponse(
        path=file_path,
        filename="kyrios-salon-frontend-v13.zip",
        media_type="application/zip"
    )

@app.get("/api/download/frontend-production")
async def download_frontend_production():
    file_path = "/app/kyrios-salon-frontend-PRODUCTION.zip"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Fichier non trouvé")
    return FileResponse(
        path=file_path,
        filename="kyrios-salon-frontend-PRODUCTION.zip",
        media_type="application/zip"
    )

