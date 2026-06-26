"""
Migration Script: Compress existing base64 images
This reduces the size of base64 images stored in MongoDB by compressing them
"""
import asyncio
import os
import base64
import logging
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from image_storage import compress_image, is_base64_image

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]


def compress_base64_image(base64_data: str) -> tuple:
    """
    Compress a base64 image and return new base64 data
    Returns (new_base64, original_size, compressed_size)
    """
    try:
        if not base64_data or not base64_data.startswith('data:'):
            return base64_data, 0, 0
        
        # Parse data URL
        header, data = base64_data.split(',', 1)
        content_type = header.split(':')[1].split(';')[0]
        
        # Decode
        original_data = base64.b64decode(data)
        original_size = len(original_data)
        
        # Compress
        compressed_data, new_type = compress_image(original_data, content_type)
        compressed_size = len(compressed_data)
        
        # Only use compressed if it's actually smaller
        if compressed_size < original_size:
            new_b64 = base64.b64encode(compressed_data).decode('utf-8')
            return f"data:{new_type};base64,{new_b64}", original_size, compressed_size
        else:
            return base64_data, original_size, original_size
            
    except Exception as e:
        logger.error(f"Error compressing base64: {e}")
        return base64_data, 0, 0


async def compress_collection_images(collection_name: str, image_fields: list):
    """Compress images in a collection"""
    collection = db[collection_name]
    compressed_count = 0
    total_saved = 0
    
    logger.info(f"Processing {collection_name}...")
    
    async for doc in collection.find({}):
        updates = {}
        
        for field in image_fields:
            value = doc.get(field)
            
            # Handle single image field
            if isinstance(value, str) and is_base64_image(value):
                new_value, orig_size, comp_size = compress_base64_image(value)
                if comp_size < orig_size:
                    updates[field] = new_value
                    total_saved += (orig_size - comp_size)
                    logger.info(f"  Compressed {field}: {orig_size} -> {comp_size} bytes")
            
            # Handle array of images
            elif isinstance(value, list):
                new_list = []
                changed = False
                for item in value:
                    if isinstance(item, dict) and is_base64_image(item.get('url', '')):
                        new_url, orig_size, comp_size = compress_base64_image(item['url'])
                        if comp_size < orig_size:
                            item['url'] = new_url
                            total_saved += (orig_size - comp_size)
                            changed = True
                    new_list.append(item)
                if changed:
                    updates[field] = new_list
        
        if updates:
            await collection.update_one({"_id": doc["_id"]}, {"$set": updates})
            compressed_count += 1
    
    logger.info(f"  {collection_name}: {compressed_count} documents updated")
    return compressed_count, total_saved


async def run_compression():
    """Run compression on all collections with images"""
    logger.info("=" * 50)
    logger.info("Starting image compression")
    logger.info("=" * 50)
    
    total_docs = 0
    total_saved = 0
    
    collections = [
        ("products", ["image_url"]),
        ("wigs", ["image_url", "media"]),
        ("shop_products", ["image_url", "media"]),
        ("service_categories", ["image_url"]),
        ("site_content", ["hero_image", "about_image"]),
        ("announcements", ["image_url"]),
        ("media_library", ["url"]),
    ]
    
    for coll_name, fields in collections:
        try:
            docs, saved = await compress_collection_images(coll_name, fields)
            total_docs += docs
            total_saved += saved
        except Exception as e:
            logger.error(f"Error processing {coll_name}: {e}")
    
    saved_mb = round(total_saved / (1024 * 1024), 2)
    logger.info("=" * 50)
    logger.info(f"Compression complete!")
    logger.info(f"Documents updated: {total_docs}")
    logger.info(f"Total space saved: {saved_mb} MB")
    logger.info("=" * 50)
    
    return total_docs, total_saved


if __name__ == "__main__":
    asyncio.run(run_compression())
