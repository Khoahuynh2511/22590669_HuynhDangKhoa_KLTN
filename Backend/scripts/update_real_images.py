"""
Script to update database placeholder images with real, high-quality Unsplash photos.
This script checks the names and destinations of both tour packages and activity packages,
and updates their image URLs to beautiful, real-world photos.

Usage:
    cd Backend
    uv run python scripts/update_real_images.py
"""

import os
import sys
import io
from pathlib import Path

# Fix Windows encoding for emoji output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

import psycopg2

def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL must be set in .env")
        sys.exit(1)
    # Convert asyncpg scheme to standard psycopg2 scheme
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres+asyncpg://", "postgresql://")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    return conn

# Unsplash high-quality image URLs for different keywords/destinations
IMAGE_MAPPING = {
    # Destinations (Tours & Activities)
    "Đà Lạt": {
        "nature": "https://images.unsplash.com/photo-1583212292454-1fe6229603b7?auto=format&fit=crop&w=1000&q=80", # Pine hills Dalat
        "lake": "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1000&q=80", # Scenic lake
        "cafe": "https://images.unsplash.com/photo-1498804103079-a6351b050096?auto=format&fit=crop&w=1000&q=80", # Cozy cafe/outdoor
        "strawberry": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1000&q=80", # Mountain farm/berries
        "default": "https://images.unsplash.com/photo-1583212292454-1fe6229603b7?auto=format&fit=crop&w=1000&q=80"
    },
    "Sapa": {
        "nature": "https://images.unsplash.com/photo-1508873696983-2df519f0397e?auto=format&fit=crop&w=1000&q=80", # Terraced fields
        "trekking": "https://images.unsplash.com/photo-1508873696983-2df519f0397e?auto=format&fit=crop&w=1000&q=80",
        "culture": "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1000&q=80", # Vietnam mountain village
        "default": "https://images.unsplash.com/photo-1508873696983-2df519f0397e?auto=format&fit=crop&w=1000&q=80"
    },
    "Phú Quốc": {
        "beach": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1000&q=80", # Tropical beach
        "sunset": "https://images.unsplash.com/photo-1501179691627-eeaa65ea017c?auto=format&fit=crop&w=1000&q=80", # Beach sunset
        "safari": "https://images.unsplash.com/photo-1534567153574-2b12153a87f0?auto=format&fit=crop&w=1000&q=80", # Wild animals
        "default": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1000&q=80"
    },
    "Nha Trang": {
        "beach": "https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=1000&q=80", # Nha Trang/Vietnam bay
        "cruise": "https://images.unsplash.com/photo-1505080856163-267d49b300cac?auto=format&fit=crop&w=1000&q=80", # Luxury yacht/sea
        "spa": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=1000&q=80", # Mudbath/relaxation
        "default": "https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=1000&q=80"
    },
    "Đà Nẵng": {
        "bridge": "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?auto=format&fit=crop&w=1000&q=80", # Golden Bridge
        "beach": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1000&q=80",
        "default": "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?auto=format&fit=crop&w=1000&q=80"
    },
    "Hội An": {
        "town": "https://images.unsplash.com/photo-1605538032432-a9f0c8d9baac?auto=format&fit=crop&w=1000&q=80", # Lantern street
        "default": "https://images.unsplash.com/photo-1605538032432-a9f0c8d9baac?auto=format&fit=crop&w=1000&q=80"
    },
    "Vũng Tàu": {
        "beach": "https://images.unsplash.com/photo-1519046904884-53103b34b206?auto=format&fit=crop&w=1000&q=80", # Sandy beach
        "default": "https://images.unsplash.com/photo-1519046904884-53103b34b206?auto=format&fit=crop&w=1000&q=80"
    },
    "default": {
        "nature": "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1000&q=80", # Waterfall/nature
        "beach": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1000&q=80",
        "food": "https://images.unsplash.com/photo-1563245372-f21724e3856d?auto=format&fit=crop&w=1000&q=80", # Vietnamese food
        "culture": "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1000&q=80",
        "default": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=1000&q=80" # General travel
    }
}

def determine_activity_image(name, destination, category):
    dest_map = IMAGE_MAPPING.get(destination, IMAGE_MAPPING["default"])
    name_lower = name.lower()
    
    # 1. Match specific sub-themes by name keywords
    if "hồ" in name_lower or "xuân hương" in name_lower:
        return dest_map.get("lake", dest_map["default"])
    elif "dâu" in name_lower or "vườn dâu" in name_lower or "chè" in name_lower or "đồi chè" in name_lower:
        return dest_map.get("strawberry", dest_map["default"])
    elif "cafe" in name_lower or "cà phê" in name_lower or "chợ đêm" in name_lower or "nightlife" in name_lower:
        return dest_map.get("cafe", IMAGE_MAPPING["default"]["food"])
    elif "tắm bùn" in name_lower or "spa" in name_lower or "thiền viện" in name_lower or "trúc lâm" in name_lower:
        return dest_map.get("spa", IMAGE_MAPPING["default"]["nature"])
    elif "du thuyền" in name_lower or "cruise" in name_lower:
        return dest_map.get("cruise", dest_map["default"])
    elif "safari" in name_lower or "vườn thú" in name_lower:
        return dest_map.get("safari", dest_map["default"])
    elif "hoàng hôn" in name_lower or "sunset" in name_lower:
        return dest_map.get("sunset", dest_map["default"])
    
    # 2. Match by category keyword
    if category == "nature":
        return dest_map.get("nature", dest_map["default"])
    elif category == "adventure":
        return dest_map.get("trekking", dest_map.get("nature", dest_map["default"]))
    elif category == "food":
        return IMAGE_MAPPING["default"]["food"]
    elif category == "relax" or category == "spiritual":
        return dest_map.get("spa", dest_map.get("lake", dest_map["default"]))
        
    return dest_map["default"]

def determine_tour_image(name, destination):
    dest_map = IMAGE_MAPPING.get(destination, IMAGE_MAPPING["default"])
    name_lower = name.lower()
    
    if "du thuyền" in name_lower or "cruise" in name_lower:
        return dest_map.get("cruise", dest_map["default"])
    elif "hoàng hôn" in name_lower or "sunset" in name_lower:
        return dest_map.get("sunset", dest_map["default"])
    elif "cắm trại" in name_lower or "camping" in name_lower or "trekking" in name_lower:
        return dest_map.get("trekking", dest_map.get("nature", dest_map["default"]))
    elif "cáp treo" in name_lower or "bà nà" in name_lower or "cầu vàng" in name_lower:
        return dest_map.get("bridge", dest_map["default"])
    
    return dest_map["default"]

def update_images():
    conn = get_connection()
    cur = conn.cursor()
    
    print("🌅 Updating Activity Packages images...")
    cur.execute("SELECT activity_id, name, destination, category, image_url FROM activity_packages")
    activities = cur.fetchall()
    
    act_updated = 0
    for act_id, name, destination, category, current_url in activities:
        # Check if it's using the default Cloudinary placeholder
        if not current_url or "cloudinary.com/demo" in current_url or "via.placeholder" in current_url or "sample.jpg" in current_url:
            new_url = determine_activity_image(name, destination, category)
            cur.execute(
                "UPDATE activity_packages SET image_url = %s, updated_at = NOW() WHERE activity_id = %s",
                (new_url, act_id)
            )
            print(f"  Updated Activity: '{name}' -> Real Photo")
            act_updated += 1
            
    print(f"✅ Finished Activity Packages. Updated {act_updated} activities.")
    
    print("\n🌅 Updating Tour Packages images...")
    cur.execute("SELECT package_id, package_name, destination, image_urls FROM tour_packages")
    tours = cur.fetchall()
    
    tours_updated = 0
    for pkg_id, name, destination, current_urls in tours:
        # If it has a placeholder or empty image URLs
        # Note: image_urls can contain multiple URLs separated by '|'
        has_placeholder = not current_urls or any(
            x in current_urls for x in ["via.placeholder", "demo/image", "sample.jpg", "test1.jpg"]
        )
        
        # We can also check if CMC domain is used, but since vietravel CMC photos might be real, 
        # we can replace them if they are broken or if the user wants beautiful Unsplash ones.
        # Let's replace if they contain placeholders or if we want a fresh look.
        if has_placeholder:
            new_url = determine_tour_image(name, destination)
            cur.execute(
                "UPDATE tour_packages SET image_urls = %s, updated_at = NOW() WHERE package_id = %s",
                (new_url, pkg_id)
            )
            print(f"  Updated Tour: '{name}' -> Real Photo")
            tours_updated += 1
            
    print(f"✅ Finished Tour Packages. Updated {tours_updated} tours.")
    
    conn.commit()
    cur.close()
    conn.close()
    print("\n🎉 All image updates completed successfully!")

if __name__ == "__main__":
    update_images()
