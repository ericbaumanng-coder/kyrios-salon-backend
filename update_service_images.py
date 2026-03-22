"""
Update services with images for booking display
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Service images mapped by service name keywords
SERVICE_IMAGES = {
    # Box Braids
    "Box Braids": "https://images.unsplash.com/photo-1711637819201-1f2671641b4e?w=400&h=400&fit=crop",
    
    # Knotless Braids
    "Knotless Braids": "https://images.pexels.com/photos/7078204/pexels-photo-7078204.jpeg?w=400&h=400&fit=crop",
    
    # Senegalese Twists
    "Senegalese Twists": "https://images.pexels.com/photos/36297542/pexels-photo-36297542.jpeg?w=400&h=400&fit=crop",
    
    # Goddess Braids
    "Goddess Braids": "https://images.unsplash.com/photo-1768489134736-af8149e8fef1?w=400&h=400&fit=crop",
    
    # Ghana Braids
    "Ghana Braids": "https://images.pexels.com/photos/5672899/pexels-photo-5672899.jpeg?w=400&h=400&fit=crop",
    
    # Cornrows
    "Cornrows": "https://images.pexels.com/photos/4671331/pexels-photo-4671331.jpeg?w=400&h=400&fit=crop",
    
    # Tissage
    "Tissage": "https://images.pexels.com/photos/6923373/pexels-photo-6923373.jpeg?w=400&h=400&fit=crop",
    
    # Pose Closure
    "Pose Closure": "https://images.unsplash.com/photo-1661818302487-467621dd1c19?w=400&h=400&fit=crop",
    
    # Pose Frontale
    "Pose Frontale": "https://images.unsplash.com/photo-1588527962980-72746d95973e?w=400&h=400&fit=crop",
    
    # Pose Ponytail
    "Pose Ponytail": "https://images.unsplash.com/photo-1770182023775-4706ce1bed72?w=400&h=400&fit=crop",
    
    # 360 Frontale / Full Lace
    "360 Frontale": "https://images.pexels.com/photos/6923213/pexels-photo-6923213.jpeg?w=400&h=400&fit=crop",
    
    # Locks
    "Locks Start": "https://images.pexels.com/photos/3186970/pexels-photo-3186970.jpeg?w=400&h=400&fit=crop",
    "Locks Maintenance": "https://images.unsplash.com/photo-1765560216633-05f34712f3d4?w=400&h=400&fit=crop",
    "Locks Retouch": "https://images.unsplash.com/photo-1765560216325-e9dcf84ac25c?w=400&h=400&fit=crop",
    
    # Soins
    "Soin Deep Treatment": "https://images.pexels.com/photos/7755473/pexels-photo-7755473.jpeg?w=400&h=400&fit=crop",
    "Brushing": "https://images.pexels.com/photos/3993451/pexels-photo-3993451.jpeg?w=400&h=400&fit=crop",
    "Dégradé": "https://images.pexels.com/photos/3993451/pexels-photo-3993451.jpeg?w=400&h=400&fit=crop",
    "Lissage Kératine": "https://images.pexels.com/photos/3356211/pexels-photo-3356211.jpeg?w=400&h=400&fit=crop",
    "Coupe + Soin": "https://images.pexels.com/photos/6503332/pexels-photo-6503332.jpeg?w=400&h=400&fit=crop",
}

async def update_service_images():
    print("Updating service images...")
    
    services = await db.services.find({}).to_list(100)
    
    for service in services:
        service_name = service.get('name', '')
        image_url = None
        
        # Find matching image
        for keyword, url in SERVICE_IMAGES.items():
            if keyword in service_name:
                image_url = url
                break
        
        if image_url:
            await db.services.update_one(
                {"id": service['id']},
                {"$set": {"image_url": image_url}}
            )
            print(f"  Updated: {service_name} -> {image_url[:50]}...")
        else:
            # Default image for services without specific image
            default_url = "https://images.pexels.com/photos/3993451/pexels-photo-3993451.jpeg?w=400&h=400&fit=crop"
            await db.services.update_one(
                {"id": service['id']},
                {"$set": {"image_url": default_url}}
            )
            print(f"  Default: {service_name}")
    
    print(f"\n✅ Updated {len(services)} services with images")


if __name__ == "__main__":
    asyncio.run(update_service_images())
