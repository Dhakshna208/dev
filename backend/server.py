from fastapi import FastAPI, APIRouter, HTTPException, Path
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path as PathLib
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = PathLib(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models for Supermarket Trolley Assistant
class Store(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    address: str
    layout_svg: str  # SVG content for the store map
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StoreCreate(BaseModel):
    name: str
    address: str
    layout_svg: str

class Section(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    store_id: str
    name: str
    color: str
    svg_element_id: str  # ID of the SVG element to highlight

class SectionCreate(BaseModel):
    store_id: str
    name: str
    color: str
    svg_element_id: str

class Category(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    store_id: str
    section_id: str
    name: str
    color: str

class CategoryCreate(BaseModel):
    store_id: str
    section_id: str
    name: str
    color: str

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category_id: str
    section_id: str
    name: str
    price: Optional[float] = 0.0
    description: Optional[str] = ""

class ProductCreate(BaseModel):
    category_id: str
    section_id: str
    name: str
    price: Optional[float] = 0.0
    description: Optional[str] = ""

class StoreData(BaseModel):
    store: Store
    sections: List[Section]
    categories: List[Category]
    products: List[Product]


# Helper functions
def prepare_for_mongo(data):
    """Convert datetime objects to ISO strings for MongoDB storage"""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = prepare_for_mongo(value)
            elif isinstance(value, list):
                result[key] = [prepare_for_mongo(item) if isinstance(item, dict) else item for item in value]
            else:
                result[key] = value
        return result
    return data

def parse_from_mongo(item):
    """Parse datetime strings back from MongoDB"""
    if isinstance(item, dict):
        result = {}
        for key, value in item.items():
            if key == 'created_at' and isinstance(value, str):
                try:
                    result[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = parse_from_mongo(value)
            elif isinstance(value, list):
                result[key] = [parse_from_mongo(item) if isinstance(item, dict) else item for item in value]
            else:
                result[key] = value
        return result
    return item


# API Routes

@api_router.get("/")
async def root():
    return {"message": "Smart Supermarket Trolley Assistant API"}

# Store routes
@api_router.post("/stores", response_model=Store)
async def create_store(store_data: StoreCreate):
    store_dict = store_data.dict()
    store_obj = Store(**store_dict)
    store_mongo = prepare_for_mongo(store_obj.dict())
    await db.stores.insert_one(store_mongo)
    return store_obj

@api_router.get("/stores", response_model=List[Store])
async def get_stores():
    stores = await db.stores.find().to_list(1000)
    return [Store(**parse_from_mongo(store)) for store in stores]

@api_router.get("/stores/{store_id}", response_model=StoreData)
async def get_store(store_id: str = Path(..., description="Store ID")):
    # Get store
    store = await db.stores.find_one({"id": store_id})
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    # Get sections
    sections = await db.sections.find({"store_id": store_id}).to_list(1000)
    
    # Get categories
    categories = await db.categories.find({"store_id": store_id}).to_list(1000)
    
    # Get products
    products = await db.products.find({"category_id": {"$in": [cat["id"] for cat in categories]}}).to_list(1000)
    
    return StoreData(
        store=Store(**parse_from_mongo(store)),
        sections=[Section(**section) for section in sections],
        categories=[Category(**category) for category in categories],
        products=[Product(**product) for product in products]
    )

# Section routes
@api_router.post("/sections", response_model=Section)
async def create_section(section_data: SectionCreate):
    section_obj = Section(**section_data.dict())
    await db.sections.insert_one(section_obj.dict())
    return section_obj

# Category routes
@api_router.post("/categories", response_model=Category)
async def create_category(category_data: CategoryCreate):
    category_obj = Category(**category_data.dict())
    await db.categories.insert_one(category_obj.dict())
    return category_obj

@api_router.get("/categories/{category_id}/products", response_model=List[Product])
async def get_category_products(category_id: str = Path(..., description="Category ID")):
    products = await db.products.find({"category_id": category_id}).to_list(1000)
    return [Product(**product) for product in products]

# Product routes
@api_router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate):
    product_obj = Product(**product_data.dict())
    await db.products.insert_one(product_obj.dict())
    return product_obj

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str = Path(..., description="Product ID")):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**product)

@api_router.get("/products/search/{query}", response_model=List[Product])
async def search_products(query: str = Path(..., description="Search query")):
    # Simple text search on product names
    products = await db.products.find({
        "name": {"$regex": query, "$options": "i"}
    }).to_list(1000)
    return [Product(**product) for product in products]

# Initialize sample data route
@api_router.post("/initialize-sample-data")
async def initialize_sample_data():
    """Initialize the database with sample supermarket data"""
    
    # Clear existing data
    await db.stores.delete_many({})
    await db.sections.delete_many({})
    await db.categories.delete_many({})
    await db.products.delete_many({})
    
    # Sample SVG for supermarket layout
    sample_svg = '''<svg viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">
        <!-- Store Background -->
        <rect width="800" height="600" fill="#f8f9fa" stroke="#dee2e6" stroke-width="2"/>
        
        <!-- Entrance -->
        <rect x="350" y="550" width="100" height="50" fill="#6c757d" />
        <text x="400" y="575" text-anchor="middle" fill="white" font-size="12">ENTRANCE</text>
        
        <!-- Fruits Section -->
        <rect id="fruits-section" x="50" y="50" width="300" height="200" fill="#28a745" opacity="0.7" stroke="#20c997" stroke-width="3" rx="10"/>
        <text x="200" y="160" text-anchor="middle" fill="white" font-size="18" font-weight="bold">FRUITS & VEGETABLES</text>
        
        <!-- Snacks Section -->
        <rect id="snacks-section" x="450" y="50" width="300" height="200" fill="#fd7e14" opacity="0.7" stroke="#f8ac59" stroke-width="3" rx="10"/>
        <text x="600" y="160" text-anchor="middle" fill="white" font-size="18" font-weight="bold">SNACKS & CHIPS</text>
        
        <!-- Beverages Section -->
        <rect id="beverages-section" x="50" y="300" width="300" height="200" fill="#007bff" opacity="0.7" stroke="#17a2b8" stroke-width="3" rx="10"/>
        <text x="200" y="410" text-anchor="middle" fill="white" font-size="18" font-weight="bold">BEVERAGES</text>
        
        <!-- Household Section -->
        <rect id="household-section" x="450" y="300" width="300" height="200" fill="#6f42c1" opacity="0.7" stroke="#8e5bba" stroke-width="3" rx="10"/>
        <text x="600" y="410" text-anchor="middle" fill="white" font-size="18" font-weight="bold">HOUSEHOLD ITEMS</text>
        
        <!-- Aisles -->
        <rect x="370" y="50" width="60" height="450" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
        <text x="400" y="280" text-anchor="middle" fill="#6c757d" font-size="12" transform="rotate(-90, 400, 280)">MAIN AISLE</text>
    </svg>'''
    
    # Create sample store
    store = Store(
        name="SuperMart Central",
        address="123 Main Street, Downtown",
        layout_svg=sample_svg
    )
    store_mongo = prepare_for_mongo(store.dict())
    await db.stores.insert_one(store_mongo)
    
    # Create sections
    sections_data = [
        {"name": "Fruits & Vegetables", "color": "#28a745", "svg_element_id": "fruits-section"},
        {"name": "Snacks & Chips", "color": "#fd7e14", "svg_element_id": "snacks-section"},
        {"name": "Beverages", "color": "#007bff", "svg_element_id": "beverages-section"},
        {"name": "Household Items", "color": "#6f42c1", "svg_element_id": "household-section"}
    ]
    
    sections = []
    for section_data in sections_data:
        section = Section(
            store_id=store.id,
            name=section_data["name"],
            color=section_data["color"],
            svg_element_id=section_data["svg_element_id"]
        )
        sections.append(section)
        await db.sections.insert_one(section.dict())
    
    # Create categories
    categories_data = [
        {"name": "Fresh Fruits", "section_idx": 0},
        {"name": "Snacks", "section_idx": 1},
        {"name": "Soft Drinks", "section_idx": 2},
        {"name": "Cleaning Supplies", "section_idx": 3}
    ]
    
    categories = []
    for cat_data in categories_data:
        section = sections[cat_data["section_idx"]]
        category = Category(
            store_id=store.id,
            section_id=section.id,
            name=cat_data["name"],
            color=section.color
        )
        categories.append(category)
        await db.categories.insert_one(category.dict())
    
    # Create sample products
    products_data = [
        # Fruits
        {"name": "Fresh Apples", "price": 2.99, "category_idx": 0, "description": "Crispy red apples"},
        {"name": "Bananas", "price": 1.49, "category_idx": 0, "description": "Fresh yellow bananas"},
        {"name": "Orange Juice", "price": 3.49, "category_idx": 0, "description": "Fresh squeezed orange juice"},
        
        # Snacks
        {"name": "Potato Chips", "price": 2.49, "category_idx": 1, "description": "Crispy salted chips"},
        {"name": "Chocolate Cookies", "price": 3.99, "category_idx": 1, "description": "Double chocolate chip cookies"},
        {"name": "Mixed Nuts", "price": 5.99, "category_idx": 1, "description": "Roasted mixed nuts"},
        
        # Beverages
        {"name": "Coca Cola", "price": 1.99, "category_idx": 2, "description": "Classic cola drink"},
        {"name": "Bottled Water", "price": 0.99, "category_idx": 2, "description": "Pure spring water"},
        
        # Household
        {"name": "Dish Soap", "price": 4.49, "category_idx": 3, "description": "Lemon scented dish soap"},
        {"name": "Paper Towels", "price": 6.99, "category_idx": 3, "description": "Absorbent paper towels"}
    ]
    
    for product_data in products_data:
        category = categories[product_data["category_idx"]]
        section = sections[product_data["category_idx"]]
        product = Product(
            category_id=category.id,
            section_id=section.id,
            name=product_data["name"],
            price=product_data["price"],
            description=product_data["description"]
        )
        await db.products.insert_one(product.dict())
    
    return {"message": "Sample data initialized successfully!", "store_id": store.id}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()