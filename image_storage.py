"""
Image Storage Service - Handles file-based image storage with compression
Replaces base64 MongoDB storage for better performance
"""
import os
import uuid
import base64
import logging
from pathlib import Path
from PIL import Image
from io import BytesIO
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration
UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# Max dimensions for different image types
MAX_DIMENSIONS = {
    "thumbnail": (300, 300),
    "medium": (800, 800),
    "large": (1200, 1200),
    "original": (2000, 2000)
}

# Quality settings
JPEG_QUALITY = 85
WEBP_QUALITY = 85


def compress_image(image_data: bytes, content_type: str, max_size: Tuple[int, int] = (1200, 1200)) -> Tuple[bytes, str]:
    """
    Compress and resize image while maintaining aspect ratio
    Returns compressed image bytes and the output content type
    """
    try:
        img = Image.open(BytesIO(image_data))
        
        # Convert RGBA to RGB if necessary (for JPEG)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Resize if larger than max dimensions
        if img.width > max_size[0] or img.height > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save to buffer with compression
        buffer = BytesIO()
        
        # Use WebP for better compression, fallback to JPEG
        output_format = 'WEBP'
        output_content_type = 'image/webp'
        
        try:
            img.save(buffer, format=output_format, quality=WEBP_QUALITY, optimize=True)
        except Exception:
            # Fallback to JPEG
            output_format = 'JPEG'
            output_content_type = 'image/jpeg'
            img.save(buffer, format=output_format, quality=JPEG_QUALITY, optimize=True)
        
        buffer.seek(0)
        return buffer.read(), output_content_type
        
    except Exception as e:
        logger.error(f"Image compression error: {e}")
        # Return original if compression fails
        return image_data, content_type


def save_image_file(image_data: bytes, original_filename: str, content_type: str, compress: bool = True) -> str:
    """
    Save image to file system with optional compression
    Returns the filename (not full path)
    """
    try:
        # Generate unique filename
        ext = '.webp' if compress else Path(original_filename).suffix.lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
            ext = '.webp'
        
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOADS_DIR / unique_filename
        
        # Compress if enabled
        if compress and content_type.startswith('image/'):
            image_data, _ = compress_image(image_data, content_type)
            unique_filename = f"{uuid.uuid4().hex}.webp"
            file_path = UPLOADS_DIR / unique_filename
        
        # Write to file
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        logger.info(f"Saved image: {unique_filename} ({len(image_data)} bytes)")
        return unique_filename
        
    except Exception as e:
        logger.error(f"Error saving image file: {e}")
        raise


def get_image_path(filename: str) -> Optional[Path]:
    """Get the full path to an image file"""
    file_path = UPLOADS_DIR / filename
    if file_path.exists():
        return file_path
    return None


def delete_image_file(filename: str) -> bool:
    """Delete an image file"""
    try:
        file_path = UPLOADS_DIR / filename
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted image: {filename}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        return False


def base64_to_file(base64_data: str) -> Optional[str]:
    """
    Convert base64 data URL to file
    Returns filename if successful, None otherwise
    """
    try:
        if not base64_data or not base64_data.startswith('data:'):
            return None
        
        # Parse data URL
        header, data = base64_data.split(',', 1)
        content_type = header.split(':')[1].split(';')[0]
        
        # Decode base64
        image_data = base64.b64decode(data)
        
        # Save as file with compression
        filename = save_image_file(image_data, 'converted.webp', content_type, compress=True)
        return filename
        
    except Exception as e:
        logger.error(f"Error converting base64 to file: {e}")
        return None


def is_base64_image(url: str) -> bool:
    """Check if URL is a base64 data URL"""
    return url and url.startswith('data:image/')


def get_image_url(filename: str, backend_url: str = "") -> str:
    """Generate the URL for accessing an image"""
    if not backend_url:
        backend_url = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')
        if backend_url and not backend_url.startswith('http'):
            backend_url = f"https://{backend_url}"
    
    return f"{backend_url}/api/uploads/{filename}"
