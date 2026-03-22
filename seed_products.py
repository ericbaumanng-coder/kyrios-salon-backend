"""
Script to seed the database with Kyrios Salon / Lyrias'Hair products
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

# Lace types available
LACE_TYPES = [
    "Transparent Lace 13x4",
    "Transparent Lace 13x6",
    "HD Lace 13x4",
    "HD Lace 13x6",
    "HD Lace 2x6",
    "HD Lace 6x6",
    "HD Lace 4x4",
    "HD Lace 5x5",
    "Sans Lace"
]

# Size options
SIZES = ["10\"", "12\"", "14\"", "16\"", "18\"", "20\"", "22\"", "24\"", "26\"", "28\"", "30\""]

# Care instructions
CARE_INSTRUCTIONS = """
<h4>Instructions de lavage</h4>
<ul>
<li>Laver avec un shampooing doux sans sulfate</li>
<li>Utiliser de l'eau tiède, jamais chaude</li>
<li>Ne pas frotter, masser délicatement</li>
<li>Rincer abondamment</li>
</ul>

<h4>Séchage</h4>
<ul>
<li>Essorer délicatement avec une serviette</li>
<li>Laisser sécher à l'air libre sur un support</li>
<li>Éviter le sèche-cheveux à haute température</li>
</ul>

<h4>Entretien quotidien</h4>
<ul>
<li>Brosser délicatement avec une brosse à poils souples</li>
<li>Utiliser un spray démêlant si nécessaire</li>
<li>Ranger sur un support ou mannequin</li>
<li>Protéger la nuit avec un bonnet en satin</li>
</ul>

<h4>Conseils</h4>
<ul>
<li>Fréquence de lavage: tous les 7-10 jours</li>
<li>Appliquer un sérum pour les pointes</li>
<li>Éviter les produits contenant de l'alcool</li>
</ul>
"""

# Products data
PRODUCTS = [
    # LISSE
    {
        "name": "Perruque Lisse Premium",
        "category": "Lisse",
        "description": "Notre collection Lisse offre des cheveux d'une douceur incomparable. Parfaits pour un look élégant et sophistiqué, ces cheveux lisses tombent naturellement et brillent sous la lumière.",
        "care_instructions": CARE_INSTRUCTIONS,
        "image_url": "https://images.unsplash.com/photo-1661818302487-467621dd1c19?w=800",
        "prices_by_size": [
            {"size": "10\"", "price": 55.0},
            {"size": "12\"", "price": 60.0},
            {"size": "14\"", "price": 65.0},
            {"size": "16\"", "price": 70.0},
            {"size": "18\"", "price": 75.0},
            {"size": "20\"", "price": 80.0},
            {"size": "22\"", "price": 85.0},
            {"size": "24\"", "price": 90.0},
            {"size": "26\"", "price": 95.0},
            {"size": "28\"", "price": 100.0},
            {"size": "30\"", "price": 105.0},
        ],
        "lace_types": LACE_TYPES,
        "is_raw_hair": False,
        "is_bulk": False
    },
    # ONDULÉ
    {
        "name": "Perruque Ondulée Élégance",
        "category": "Ondulé",
        "description": "La collection Ondulée apporte volume et mouvement naturel. Ces ondulations légères créent un look décontracté et glamour, parfait pour toutes les occasions.",
        "care_instructions": CARE_INSTRUCTIONS,
        "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800",
        "prices_by_size": [
            {"size": "10\"", "price": 65.0},
            {"size": "12\"", "price": 70.0},
            {"size": "14\"", "price": 75.0},
            {"size": "16\"", "price": 80.0},
            {"size": "18\"", "price": 85.0},
            {"size": "20\"", "price": 90.0},
            {"size": "22\"", "price": 95.0},
            {"size": "24\"", "price": 100.0},
            {"size": "26\"", "price": 105.0},
            {"size": "28\"", "price": 110.0},
            {"size": "30\"", "price": 115.0},
        ],
        "lace_types": LACE_TYPES,
        "is_raw_hair": False,
        "is_bulk": False
    },
    # BOUCLÉ
    {
        "name": "Perruque Bouclée Naturelle",
        "category": "Bouclé",
        "description": "Notre collection Bouclée célèbre la beauté des boucles naturelles. Des boucles définies et rebondissantes qui ajoutent volume et personnalité à votre style.",
        "care_instructions": CARE_INSTRUCTIONS,
        "image_url": "https://images.unsplash.com/photo-1606752444985-bf488e032cea?w=800",
        "prices_by_size": [
            {"size": "10\"", "price": 60.0},
            {"size": "12\"", "price": 68.0},
            {"size": "14\"", "price": 76.0},
            {"size": "16\"", "price": 84.0},
            {"size": "18\"", "price": 92.0},
            {"size": "20\"", "price": 100.0},
            {"size": "22\"", "price": 108.0},
            {"size": "24\"", "price": 116.0},
            {"size": "26\"", "price": 124.0},
            {"size": "28\"", "price": 132.0},
            {"size": "30\"", "price": 140.0},
        ],
        "lace_types": LACE_TYPES,
        "is_raw_hair": False,
        "is_bulk": False
    },
    # AFRO
    {
        "name": "Perruque Afro Magnifique",
        "category": "Afro",
        "description": "La collection Afro embrasse la texture naturelle africaine. Des cheveux texturés et volumineux pour un look authentique et audacieux.",
        "care_instructions": CARE_INSTRUCTIONS,
        "image_url": "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=800",
        "prices_by_size": [
            {"size": "10\"", "price": 65.0},
            {"size": "12\"", "price": 75.0},
            {"size": "14\"", "price": 85.0},
            {"size": "16\"", "price": 95.0},
            {"size": "18\"", "price": 105.0},
            {"size": "20\"", "price": 115.0},
            {"size": "22\"", "price": 125.0},
            {"size": "24\"", "price": 130.0},
            {"size": "26\"", "price": 135.0},
            {"size": "28\"", "price": 142.0},
            {"size": "30\"", "price": 150.0},
        ],
        "lace_types": LACE_TYPES,
        "is_raw_hair": False,
        "is_bulk": False
    },
    # RAW HAIR
    {
        "name": "Raw Hair Premium - Cheveux Vierges",
        "category": "Raw Hair",
        "description": "Notre collection Raw Hair propose des cheveux 100% vierges, non traités chimiquement. Qualité exceptionnelle pour des résultats professionnels. Prix sur devis uniquement - contactez-nous via WhatsApp pour une offre personnalisée.",
        "care_instructions": CARE_INSTRUCTIONS,
        "image_url": "https://images.pexels.com/photos/5836031/pexels-photo-5836031.jpeg?w=800",
        "prices_by_size": [
            {"size": "À partir de", "price": 90.0},
        ],
        "lace_types": LACE_TYPES,
        "is_raw_hair": True,
        "is_bulk": False
    },
    # BULK FOR BRAIDS - Naturel
    {
        "name": "Bulk for Braids - Naturel",
        "category": "Bulk for Braids",
        "subcategory": "Naturel",
        "description": "Cheveux en vrac parfaits pour les tresses et nattes. Texture naturelle non colorée, idéale pour créer des coiffures protectrices durables.",
        "care_instructions": CARE_INSTRUCTIONS,
        "image_url": "https://images.unsplash.com/photo-1595411425732-e69c1abe2763?w=800",
        "prices_by_size": [
            {"size": "20\"", "price": 72.0},
            {"size": "24\"", "price": 82.0},
            {"size": "28\"", "price": 92.0},
        ],
        "lace_types": ["Sans Lace"],
        "is_raw_hair": False,
        "is_bulk": True
    },
    # BULK FOR BRAIDS - Coloré
    {
        "name": "Bulk for Braids - Coloré",
        "category": "Bulk for Braids",
        "subcategory": "Coloré",
        "description": "Cheveux en vrac pré-colorés pour les tresses. Disponibles dans plusieurs teintes pour personnaliser vos coiffures protectrices.",
        "care_instructions": CARE_INSTRUCTIONS,
        "image_url": "https://images.unsplash.com/photo-1522337094846-8a818192de1f?w=800",
        "prices_by_size": [
            {"size": "20\"", "price": 82.0},
            {"size": "24\"", "price": 92.0},
            {"size": "28\"", "price": 97.0},
        ],
        "lace_types": ["Sans Lace"],
        "is_raw_hair": False,
        "is_bulk": True
    },
]

async def seed_database():
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Clear existing products
    await db.products.delete_many({})
    print("Cleared existing products")
    
    # Insert products
    import uuid
    from datetime import datetime, timezone
    
    for product in PRODUCTS:
        product["id"] = str(uuid.uuid4())
        product["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.products.insert_one(product)
        print(f"Added: {product['name']}")
    
    print(f"\nSeeded {len(PRODUCTS)} products successfully!")
    
    # Create indexes
    await db.products.create_index("id", unique=True)
    await db.products.create_index("category")
    await db.carts.create_index("session_id", unique=True)
    await db.orders.create_index("id", unique=True)
    await db.orders.create_index("order_number", unique=True)
    await db.orders.create_index("stripe_session_id")
    await db.payment_transactions.create_index("session_id", unique=True)
    
    print("Created indexes")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
