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
    
    # Sample SVG for complex supermarket layout
    sample_svg = '''<svg viewBox="0 0 1200 800" xmlns="http://www.w3.org/2000/svg">
        <!-- Store Background -->
        <rect width="1200" height="800" fill="#f8f9fa" stroke="#dee2e6" stroke-width="2"/>
        
        <!-- Entrance Area -->
        <rect x="550" y="750" width="100" height="50" fill="#6c757d" />
        <text x="600" y="775" text-anchor="middle" fill="white" font-size="14" font-weight="bold">ENTRANCE</text>
        
        <!-- Main Entrance Aisle (Vertical) -->
        <rect x="580" y="650" width="40" height="100" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
        <text x="600" y="700" text-anchor="middle" fill="#6c757d" font-size="10" transform="rotate(-90, 600, 700)">MAIN ENTRANCE</text>
        
        <!-- Customer Service & Pharmacy (Front Right) -->
        <rect id="service-section" x="650" y="650" width="200" height="80" fill="#17a2b8" opacity="0.7" stroke="#117a8b" stroke-width="3" rx="5"/>
        <text x="750" y="695" text-anchor="middle" fill="white" font-size="12" font-weight="bold">CUSTOMER SERVICE</text>
        
        <!-- Bakery (Front Left) -->
        <rect id="bakery-section" x="350" y="650" width="200" height="80" fill="#fd7e14" opacity="0.7" stroke="#e55a00" stroke-width="3" rx="5"/>
        <text x="450" y="695" text-anchor="middle" fill="white" font-size="12" font-weight="bold">FRESH BAKERY</text>
        
        <!-- Produce Section (Front Center-Left) -->
        <rect id="produce-section" x="100" y="500" width="250" height="120" fill="#28a745" opacity="0.7" stroke="#20c997" stroke-width="3" rx="5"/>
        <text x="225" y="570" text-anchor="middle" fill="white" font-size="14" font-weight="bold">FRESH PRODUCE</text>
        <text x="225" y="590" text-anchor="middle" fill="white" font-size="11">Fruits & Vegetables</text>
        
        <!-- Deli & Meat Counter (Front Right) -->
        <rect id="deli-section" x="850" y="500" width="250" height="120" fill="#dc3545" opacity="0.7" stroke="#c02938" stroke-width="3" rx="5"/>
        <text x="975" y="560" text-anchor="middle" fill="white" font-size="14" font-weight="bold">DELI & MEATS</text>
        <text x="975" y="580" text-anchor="middle" fill="white" font-size="11">Fresh Cut Daily</text>
        
        <!-- Dairy Section (Back Right) -->
        <rect id="dairy-section" x="950" y="300" width="200" height="150" fill="#6f42c1" opacity="0.7" stroke="#5a2d8c" stroke-width="3" rx="5"/>
        <text x="1050" y="370" text-anchor="middle" fill="white" font-size="12" font-weight="bold">DAIRY</text>
        <text x="1050" y="390" text-anchor="middle" fill="white" font-size="11">Milk, Cheese, Yogurt</text>
        
        <!-- Frozen Foods (Back Left) -->
        <rect id="frozen-section" x="50" y="300" width="200" height="150" fill="#007bff" opacity="0.7" stroke="#0056b3" stroke-width="3" rx="5"/>
        <text x="150" y="370" text-anchor="middle" fill="white" font-size="12" font-weight="bold">FROZEN FOODS</text>
        <text x="150" y="390" text-anchor="middle" fill="white" font-size="11">Ice Cream & Frozen</text>
        
        <!-- Aisle 1: Beverages -->
        <rect id="beverages-section" x="300" y="400" width="150" height="80" fill="#17a2b8" opacity="0.7" stroke="#117a8b" stroke-width="3" rx="5"/>
        <text x="375" y="430" text-anchor="middle" fill="white" font-size="10" font-weight="bold">AISLE 1</text>
        <text x="375" y="450" text-anchor="middle" fill="white" font-size="11">BEVERAGES</text>
        <text x="375" y="465" text-anchor="middle" fill="white" font-size="9">Soda, Juice, Water</text>
        
        <!-- Aisle 2: Snacks & Chips -->
        <rect id="snacks-section" x="480" y="400" width="150" height="80" fill="#fd7e14" opacity="0.7" stroke="#e55a00" stroke-width="3" rx="5"/>
        <text x="555" y="430" text-anchor="middle" fill="white" font-size="10" font-weight="bold">AISLE 2</text>
        <text x="555" y="450" text-anchor="middle" fill="white" font-size="11">SNACKS</text>
        <text x="555" y="465" text-anchor="middle" fill="white" font-size="9">Chips, Crackers, Nuts</text>
        
        <!-- Aisle 3: Cereal & Breakfast -->
        <rect id="cereal-section" x="660" y="400" width="150" height="80" fill="#ffc107" opacity="0.7" stroke="#d39e00" stroke-width="3" rx="5"/>
        <text x="735" y="430" text-anchor="middle" fill="white" font-size="10" font-weight="bold">AISLE 3</text>
        <text x="735" y="450" text-anchor="middle" fill="white" font-size="11">CEREAL</text>
        <text x="735" y="465" text-anchor="middle" fill="white" font-size="9">Breakfast Items</text>
        
        <!-- Aisle 4: Canned Goods -->
        <rect id="canned-section" x="300" y="250" width="150" height="80" fill="#6c757d" opacity="0.7" stroke="#5a6268" stroke-width="3" rx="5"/>
        <text x="375" y="280" text-anchor="middle" fill="white" font-size="10" font-weight="bold">AISLE 4</text>
        <text x="375" y="300" text-anchor="middle" fill="white" font-size="11">CANNED GOODS</text>
        <text x="375" y="315" text-anchor="middle" fill="white" font-size="9">Soup, Sauce, Beans</text>
        
        <!-- Aisle 5: Pasta & International -->
        <rect id="pasta-section" x="480" y="250" width="150" height="80" fill="#e83e8c" opacity="0.7" stroke="#d91a72" stroke-width="3" rx="5"/>
        <text x="555" y="280" text-anchor="middle" fill="white" font-size="10" font-weight="bold">AISLE 5</text>
        <text x="555" y="300" text-anchor="middle" fill="white" font-size="11">PASTA</text>
        <text x="555" y="315" text-anchor="middle" fill="white" font-size="9">International Foods</text>
        
        <!-- Aisle 6: Baking & Spices -->
        <rect id="baking-section" x="660" y="250" width="150" height="80" fill="#20c997" opacity="0.7" stroke="#17a085" stroke-width="3" rx="5"/>
        <text x="735" y="280" text-anchor="middle" fill="white" font-size="10" font-weight="bold">AISLE 6</text>
        <text x="735" y="300" text-anchor="middle" fill="white" font-size="11">BAKING</text>
        <text x="735" y="315" text-anchor="middle" fill="white" font-size="9">Flour, Sugar, Spices</text>
        
        <!-- Aisle 7: Health & Beauty -->
        <rect id="health-section" x="300" y="100" width="150" height="80" fill="#6f42c1" opacity="0.7" stroke="#5a2d8c" stroke-width="3" rx="5"/>
        <text x="375" y="130" text-anchor="middle" fill="white" font-size="10" font-weight="bold">AISLE 7</text>
        <text x="375" y="150" text-anchor="middle" fill="white" font-size="11">HEALTH & BEAUTY</text>
        <text x="375" y="165" text-anchor="middle" fill="white" font-size="9">Personal Care</text>
        
        <!-- Aisle 8: Household & Cleaning -->
        <rect id="household-section" x="480" y="100" width="150" height="80" fill="#dc3545" opacity="0.7" stroke="#c02938" stroke-width="3" rx="5"/>
        <text x="555" y="130" text-anchor="middle" fill="white" font-size="10" font-weight="bold">AISLE 8</text>
        <text x="555" y="150" text-anchor="middle" fill="white" font-size="11">HOUSEHOLD</text>
        <text x="555" y="165" text-anchor="middle" fill="white" font-size="9">Cleaning Supplies</text>
        
        <!-- Pet Supplies (Back Center) -->
        <rect id="pet-section" x="660" y="100" width="150" height="80" fill="#795548" opacity="0.7" stroke="#5d4037" stroke-width="3" rx="5"/>
        <text x="735" y="130" text-anchor="middle" fill="white" font-size="10" font-weight="bold">PET SUPPLIES</text>
        <text x="735" y="150" text-anchor="middle" fill="white" font-size="11">Food & Accessories</text>
        
        <!-- Horizontal Aisles -->
        <rect x="280" y="190" width="550" height="30" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
        <rect x="280" y="340" width="550" height="30" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
        <rect x="280" y="490" width="550" height="30" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
        
        <!-- Vertical Aisles -->
        <rect x="270" y="90" width="30" height="430" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
        <rect x="460" y="90" width="30" height="430" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
        <rect x="640" y="90" width="30" height="430" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
        <rect x="820" y="90" width="30" height="430" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
        
        <!-- Direction Arrows for Navigation -->
        <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#28a745" />
            </marker>
        </defs>
        
        <!-- Store Labels -->
        <text x="600" y="30" text-anchor="middle" fill="#343a40" font-size="18" font-weight="bold">SuperMart Central - Complex Layout</text>
        <text x="50" y="60" fill="#6c757d" font-size="12">← Frozen Foods</text>
        <text x="1050" y="60" fill="#6c757d" font-size="12">Dairy →</text>
    </svg>'''
    
    # Create sample store
    store = Store(
        name="SuperMart Central",
        address="123 Main Street, Downtown",
        layout_svg=sample_svg
    )
    store_mongo = prepare_for_mongo(store.dict())
    await db.stores.insert_one(store_mongo)
    
    # Create sections for complex layout
    sections_data = [
        {"name": "Fresh Produce", "color": "#28a745", "svg_element_id": "produce-section"},
        {"name": "Beverages", "color": "#17a2b8", "svg_element_id": "beverages-section"},
        {"name": "Snacks & Chips", "color": "#fd7e14", "svg_element_id": "snacks-section"},
        {"name": "Cereal & Breakfast", "color": "#ffc107", "svg_element_id": "cereal-section"},
        {"name": "Canned Goods", "color": "#6c757d", "svg_element_id": "canned-section"},
        {"name": "Pasta & International", "color": "#e83e8c", "svg_element_id": "pasta-section"},
        {"name": "Baking & Spices", "color": "#20c997", "svg_element_id": "baking-section"},
        {"name": "Health & Beauty", "color": "#6f42c1", "svg_element_id": "health-section"},
        {"name": "Household & Cleaning", "color": "#dc3545", "svg_element_id": "household-section"},
        {"name": "Pet Supplies", "color": "#795548", "svg_element_id": "pet-section"},
        {"name": "Fresh Bakery", "color": "#fd7e14", "svg_element_id": "bakery-section"},
        {"name": "Deli & Meats", "color": "#dc3545", "svg_element_id": "deli-section"},
        {"name": "Dairy", "color": "#6f42c1", "svg_element_id": "dairy-section"},
        {"name": "Frozen Foods", "color": "#007bff", "svg_element_id": "frozen-section"}
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
    
    # Create categories with diverse products
    categories_data = [
        {"name": "Fresh Fruits", "section_idx": 0},  # Produce
        {"name": "Vegetables", "section_idx": 0},     # Produce
        {"name": "Soft Drinks", "section_idx": 1},    # Beverages
        {"name": "Juices", "section_idx": 1},         # Beverages
        {"name": "Chips & Crackers", "section_idx": 2}, # Snacks
        {"name": "Nuts & Candy", "section_idx": 2},   # Snacks
        {"name": "Breakfast Cereals", "section_idx": 3}, # Cereal
        {"name": "Canned Soup", "section_idx": 4},    # Canned
        {"name": "Pasta", "section_idx": 5},          # Pasta
        {"name": "Baking Essentials", "section_idx": 6}, # Baking
        {"name": "Personal Care", "section_idx": 7},  # Health
        {"name": "Cleaning Supplies", "section_idx": 8}, # Household
        {"name": "Pet Food", "section_idx": 9},       # Pet
        {"name": "Fresh Bread", "section_idx": 10},   # Bakery
        {"name": "Deli Meats", "section_idx": 11},    # Deli
        {"name": "Milk & Cheese", "section_idx": 12}, # Dairy
        {"name": "Ice Cream", "section_idx": 13}      # Frozen
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
    
    # Create diverse sample products for complex store
    products_data = [
        # Fresh Produce
        {"name": "Fresh Apples", "price": 2.99, "category_idx": 0, "description": "Crispy red apples"},
        {"name": "Bananas", "price": 1.49, "category_idx": 0, "description": "Fresh yellow bananas"},
        {"name": "Carrots", "price": 1.89, "category_idx": 1, "description": "Fresh organic carrots"},
        {"name": "Spinach", "price": 2.49, "category_idx": 1, "description": "Fresh baby spinach"},
        
        # Beverages  
        {"name": "Coca Cola", "price": 1.99, "category_idx": 2, "description": "Classic cola drink"},
        {"name": "Bottled Water", "price": 0.99, "category_idx": 2, "description": "Pure spring water"},
        {"name": "Orange Juice", "price": 3.49, "category_idx": 3, "description": "Fresh squeezed orange juice"},
        {"name": "Apple Juice", "price": 2.99, "category_idx": 3, "description": "100% apple juice"},
        
        # Snacks
        {"name": "Potato Chips", "price": 2.49, "category_idx": 4, "description": "Crispy salted chips"},
        {"name": "Chocolate Cookies", "price": 3.99, "category_idx": 4, "description": "Double chocolate chip cookies"},
        {"name": "Mixed Nuts", "price": 5.99, "category_idx": 5, "description": "Roasted mixed nuts"},
        {"name": "Gummy Bears", "price": 1.79, "category_idx": 5, "description": "Fruity gummy candy"},
        
        # Cereal & Breakfast
        {"name": "Corn Flakes", "price": 4.29, "category_idx": 6, "description": "Classic breakfast cereal"},
        {"name": "Granola", "price": 5.49, "category_idx": 6, "description": "Honey oat granola"},
        
        # Canned Goods
        {"name": "Chicken Soup", "price": 1.89, "category_idx": 7, "description": "Campbell's chicken noodle soup"},
        {"name": "Tomato Sauce", "price": 1.29, "category_idx": 7, "description": "Organic tomato sauce"},
        
        # Pasta & International
        {"name": "Spaghetti", "price": 1.99, "category_idx": 8, "description": "Italian spaghetti pasta"},
        {"name": "Ramen Noodles", "price": 0.89, "category_idx": 8, "description": "Instant ramen"},
        
        # Baking & Spices
        {"name": "All-Purpose Flour", "price": 2.49, "category_idx": 9, "description": "5lb bag of flour"},
        {"name": "Vanilla Extract", "price": 4.99, "category_idx": 9, "description": "Pure vanilla extract"},
        
        # Health & Beauty
        {"name": "Shampoo", "price": 6.99, "category_idx": 10, "description": "Moisturizing shampoo"},
        {"name": "Toothpaste", "price": 3.49, "category_idx": 10, "description": "Whitening toothpaste"},
        
        # Household & Cleaning
        {"name": "Dish Soap", "price": 4.49, "category_idx": 11, "description": "Lemon scented dish soap"},
        {"name": "Paper Towels", "price": 6.99, "category_idx": 11, "description": "Absorbent paper towels"},
        
        # Pet Supplies
        {"name": "Dog Food", "price": 12.99, "category_idx": 12, "description": "Premium dry dog food"},
        {"name": "Cat Treats", "price": 3.99, "category_idx": 12, "description": "Salmon flavored treats"},
        
        # Fresh Bakery
        {"name": "Sourdough Bread", "price": 3.99, "category_idx": 13, "description": "Fresh baked sourdough"},
        {"name": "Blueberry Muffins", "price": 4.99, "category_idx": 13, "description": "Pack of 6 muffins"},
        
        # Deli & Meats
        {"name": "Sliced Turkey", "price": 7.99, "category_idx": 14, "description": "Fresh sliced turkey breast"},
        {"name": "Ham", "price": 6.99, "category_idx": 14, "description": "Honey glazed ham"},
        
        # Dairy
        {"name": "Whole Milk", "price": 3.49, "category_idx": 15, "description": "1 gallon whole milk"},
        {"name": "Cheddar Cheese", "price": 4.99, "category_idx": 15, "description": "Sharp cheddar cheese"},
        
        # Frozen Foods
        {"name": "Ice Cream", "price": 5.99, "category_idx": 16, "description": "Vanilla ice cream"},
        {"name": "Frozen Pizza", "price": 4.49, "category_idx": 16, "description": "Pepperoni pizza"}
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