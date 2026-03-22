"""
Seed script for Kyrios Salon Services
Run this to populate the database with all 29 services
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
import uuid

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Service Categories
CATEGORIES = [
    {
        "id": "cat_tresses",
        "name": "Tresses & Coiffures Naturelles",
        "name_de": "Zöpfe & Natürliche Frisuren",
        "description": "Box braids, knotless, twists et plus",
        "order": 1
    },
    {
        "id": "cat_tissage",
        "name": "Tissage & Pose",
        "name_de": "Einnähen & Perückenanbringung",
        "description": "Tissage, closure, frontale et ponytail",
        "order": 2
    },
    {
        "id": "cat_locks",
        "name": "Locks",
        "name_de": "Dreadlocks",
        "description": "Création et entretien de locks",
        "order": 3
    },
    {
        "id": "cat_soins",
        "name": "Soins & Styling",
        "name_de": "Pflege & Styling",
        "description": "Soins, brushing, lissage et coupe",
        "order": 4
    }
]

# All 29 Services (based on user's exact specifications)
SERVICES = [
    # FAMILLE 1 — Tresses & Coiffures Naturelles (16 services)
    {"category_id": "cat_tresses", "name": "Box Braids S", "price": 80, "duration_minutes": 180, "order": 1},
    {"category_id": "cat_tresses", "name": "Box Braids M", "price": 120, "duration_minutes": 240, "order": 2},
    {"category_id": "cat_tresses", "name": "Box Braids L", "price": 160, "duration_minutes": 300, "order": 3},
    {"category_id": "cat_tresses", "name": "Knotless Braids S", "price": 100, "duration_minutes": 210, "order": 4},
    {"category_id": "cat_tresses", "name": "Knotless Braids M", "price": 140, "duration_minutes": 270, "order": 5},
    {"category_id": "cat_tresses", "name": "Knotless Braids L", "price": 180, "duration_minutes": 330, "order": 6},
    {"category_id": "cat_tresses", "name": "Senegalese Twists S", "price": 80, "duration_minutes": 180, "order": 7},
    {"category_id": "cat_tresses", "name": "Senegalese Twists M", "price": 120, "duration_minutes": 240, "order": 8},
    {"category_id": "cat_tresses", "name": "Senegalese Twists L", "price": 160, "duration_minutes": 300, "order": 9},
    {"category_id": "cat_tresses", "name": "Goddess Braids S", "price": 90, "duration_minutes": 180, "order": 10},
    {"category_id": "cat_tresses", "name": "Goddess Braids M", "price": 130, "duration_minutes": 240, "order": 11},
    {"category_id": "cat_tresses", "name": "Goddess Braids L", "price": 170, "duration_minutes": 300, "order": 12},
    {"category_id": "cat_tresses", "name": "Ghana Braids S", "price": 70, "duration_minutes": 150, "order": 13},
    {"category_id": "cat_tresses", "name": "Ghana Braids L", "price": 130, "duration_minutes": 240, "order": 14},
    {"category_id": "cat_tresses", "name": "Cornrows Simple", "price": 40, "duration_minutes": 60, "order": 15},
    {"category_id": "cat_tresses", "name": "Cornrows Complexes", "price": 90, "duration_minutes": 150, "order": 16},
    
    # FAMILLE 2 — Tissage & Pose (5 services)
    {"category_id": "cat_tissage", "name": "Tissage", "price": 80, "duration_minutes": 90, "order": 1},
    {"category_id": "cat_tissage", "name": "Pose Closure", "price": 60, "duration_minutes": 90, "order": 2},
    {"category_id": "cat_tissage", "name": "Pose Frontale", "price": 80, "duration_minutes": 120, "order": 3},
    {"category_id": "cat_tissage", "name": "Pose Ponytail", "price": 50, "duration_minutes": 60, "order": 4},
    {"category_id": "cat_tissage", "name": "360 Frontale / Full Lace", "price": 120, "duration_minutes": 150, "order": 5},
    
    # FAMILLE 3 — Locks (3 services)
    {"category_id": "cat_locks", "name": "Locks Start", "price": 150, "duration_minutes": 180, "order": 1},
    {"category_id": "cat_locks", "name": "Locks Maintenance", "price": 60, "duration_minutes": 90, "order": 2},
    {"category_id": "cat_locks", "name": "Locks Retouch", "price": 40, "duration_minutes": 60, "order": 3},
    
    # FAMILLE 4 — Soins & Styling (5 services)
    {"category_id": "cat_soins", "name": "Soin Deep Treatment", "price": 50, "duration_minutes": 60, "order": 1},
    {"category_id": "cat_soins", "name": "Brushing", "price": 30, "duration_minutes": 45, "order": 2},
    {"category_id": "cat_soins", "name": "Dégradé", "price": 35, "duration_minutes": 45, "order": 3},
    {"category_id": "cat_soins", "name": "Lissage Kératine", "price": 120, "duration_minutes": 120, "order": 4},
    {"category_id": "cat_soins", "name": "Coupe + Soin", "price": 45, "duration_minutes": 60, "order": 5},
]

# Default availability (Wednesday to Saturday, 7:30 - 18:30)
AVAILABILITY = [
    {"id": str(uuid.uuid4()), "day_of_week": 2, "start_time": "07:30", "end_time": "18:30", "is_active": True},  # Wednesday
    {"id": str(uuid.uuid4()), "day_of_week": 3, "start_time": "07:30", "end_time": "18:30", "is_active": True},  # Thursday
    {"id": str(uuid.uuid4()), "day_of_week": 4, "start_time": "07:30", "end_time": "18:30", "is_active": True},  # Friday
    {"id": str(uuid.uuid4()), "day_of_week": 5, "start_time": "07:30", "end_time": "18:30", "is_active": True},  # Saturday
]


async def seed_services():
    print("Seeding service categories...")
    
    # Clear existing data
    await db.service_categories.delete_many({})
    await db.services.delete_many({})
    await db.availability.delete_many({})
    
    # Insert categories
    for cat in CATEGORIES:
        await db.service_categories.insert_one(cat)
        print(f"  Created category: {cat['name']}")
    
    print("\nSeeding services...")
    
    # Insert services
    for service in SERVICES:
        service_doc = {
            "id": str(uuid.uuid4()),
            "category_id": service["category_id"],
            "name": service["name"],
            "price": service["price"],
            "duration_minutes": service["duration_minutes"],
            "image_url": None,  # Can be updated later
            "is_active": True,
            "order": service["order"]
        }
        await db.services.insert_one(service_doc)
        print(f"  Created service: {service['name']} - {service['price']} CHF / {service['duration_minutes']}min")
    
    print("\nSeeding availability...")
    
    # Insert availability
    days = {2: "Mercredi", 3: "Jeudi", 4: "Vendredi", 5: "Samedi"}
    for avail in AVAILABILITY:
        await db.availability.insert_one(avail)
        print(f"  Set availability: {days[avail['day_of_week']]} {avail['start_time']} - {avail['end_time']}")
    
    print(f"\n✅ Seeding complete!")
    print(f"   - {len(CATEGORIES)} categories")
    print(f"   - {len(SERVICES)} services")
    print(f"   - {len(AVAILABILITY)} availability slots")


if __name__ == "__main__":
    asyncio.run(seed_services())
