import React, { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, useParams } from "react-router-dom";
import axios from "axios";
import { Search, MapPin, ShoppingCart, Package, Plus, Minus, Navigation, ArrowRight, ArrowLeft, ArrowUp, Check } from "lucide-react";
import { Input } from "./components/ui/input";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Home Page Component
const Home = () => {
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStores = async () => {
      try {
        const response = await axios.get(`${API}/stores`);
        setStores(response.data);
      } catch (error) {
        console.error('Error fetching stores:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStores();
  }, []);

  const initializeSampleData = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/initialize-sample-data`);
      console.log('Sample data initialized:', response.data);
      // Refresh stores list
      const storesResponse = await axios.get(`${API}/stores`);
      setStores(storesResponse.data);
    } catch (error) {
      console.error('Error initializing sample data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-12">
          <ShoppingCart className="h-16 w-16 text-emerald-600 mx-auto mb-4" />
          <h1 className="text-4xl font-bold text-gray-800 mb-2">Smart Trolley Assistant</h1>
          <p className="text-gray-600 text-lg">Find products easily with our interactive store maps</p>
        </div>

        {stores.length === 0 ? (
          <div className="text-center">
            <Card className="max-w-md mx-auto">
              <CardContent className="p-8">
                <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">No Stores Available</h3>
                <p className="text-gray-600 mb-6">Get started by initializing sample store data</p>
                <Button onClick={initializeSampleData} className="w-full">
                  Initialize Sample Store
                </Button>
              </CardContent>
            </Card>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {stores.map((store) => (
              <Card key={store.id} className="hover:shadow-lg transition-shadow duration-300">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MapPin className="h-5 w-5 text-emerald-600" />
                    {store.name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600 mb-4">{store.address}</p>
                  <Button 
                    asChild 
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                  >
                    <a href={`/store/${store.id}`}>
                      View Store Map
                    </a>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Store Page Component
const StorePage = () => {
  const { storeId } = useParams();
  const [storeData, setStoreData] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [highlightedSection, setHighlightedSection] = useState(null);
  const [shoppingList, setShoppingList] = useState([]);
  const [showDirections, setShowDirections] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStoreData = async () => {
      try {
        const response = await axios.get(`${API}/stores/${storeId}`);
        setStoreData(response.data);
      } catch (error) {
        console.error('Error fetching store data:', error);
      } finally {
        setLoading(false);
      }
    };

    if (storeId) {
      fetchStoreData();
    }
  }, [storeId]);

  const handleSearch = async (query) => {
    if (query.trim() === "") {
      setSearchResults([]);
      return;
    }

    try {
      const response = await axios.get(`${API}/products/search/${encodeURIComponent(query)}`);
      setSearchResults(response.data);
    } catch (error) {
      console.error('Error searching products:', error);
      setSearchResults([]);
    }
  };

  // Calculate optimal shopping path for complex store layout
  const calculateOptimalPath = (products) => {
    if (products.length === 0) return [];
    
    // Define section positions for complex store layout (based on new SVG)
    const sectionPositions = {
      'produce-section': { x: 225, y: 560, name: 'FRESH PRODUCE', aisle: 'Front Left', landmark: 'near Bakery' },
      'beverages-section': { x: 375, y: 440, name: 'BEVERAGES', aisle: 'Aisle 1', landmark: 'center store' },
      'snacks-section': { x: 555, y: 440, name: 'SNACKS & CHIPS', aisle: 'Aisle 2', landmark: 'next to Cereal' },
      'cereal-section': { x: 735, y: 440, name: 'CEREAL & BREAKFAST', aisle: 'Aisle 3', landmark: 'center-right' },
      'canned-section': { x: 375, y: 290, name: 'CANNED GOODS', aisle: 'Aisle 4', landmark: 'back area' },
      'pasta-section': { x: 555, y: 290, name: 'PASTA & INTERNATIONAL', aisle: 'Aisle 5', landmark: 'middle back' },
      'baking-section': { x: 735, y: 290, name: 'BAKING & SPICES', aisle: 'Aisle 6', landmark: 'back right' },
      'health-section': { x: 375, y: 140, name: 'HEALTH & BEAUTY', aisle: 'Aisle 7', landmark: 'far back left' },
      'household-section': { x: 555, y: 140, name: 'HOUSEHOLD & CLEANING', aisle: 'Aisle 8', landmark: 'far back center' },
      'pet-section': { x: 735, y: 140, name: 'PET SUPPLIES', aisle: 'Back Right', landmark: 'far back corner' },
      'bakery-section': { x: 450, y: 690, name: 'FRESH BAKERY', aisle: 'Front', landmark: 'left of entrance' },
      'deli-section': { x: 975, y: 560, name: 'DELI & MEATS', aisle: 'Front Right', landmark: 'service counter' },
      'dairy-section': { x: 1050, y: 375, name: 'DAIRY', aisle: 'Right Wall', landmark: 'refrigerated section' },
      'frozen-section': { x: 150, y: 375, name: 'FROZEN FOODS', aisle: 'Left Wall', landmark: 'freezer section' }
    };
    
    // Get unique sections for products
    const sectionsNeeded = [...new Set(products.map(p => p.section_id))];
    const sectionDetails = sectionsNeeded.map(sectionId => {
      const section = storeData.sections.find(s => s.id === sectionId);
      const position = sectionPositions[section.svg_element_id];
      return {
        ...section,
        ...position,
        products: products.filter(p => p.section_id === sectionId)
      };
    });
    
    // Enhanced path optimization starting from entrance
    const entrance = { x: 600, y: 775, name: 'ENTRANCE' };
    let optimizedPath = [];
    let currentPosition = entrance;
    let remainingSections = [...sectionDetails];
    
    // Prioritize sections based on store layout logic
    const sectionPriority = {
      'bakery-section': 1,      // Front left - easy first stop
      'produce-section': 2,     // Front produce area
      'deli-section': 3,        // Front right service counter
      'beverages-section': 4,   // Aisle 1 - center store
      'snacks-section': 5,      // Aisle 2 
      'cereal-section': 6,      // Aisle 3
      'canned-section': 7,      // Aisle 4 - back area
      'pasta-section': 8,       // Aisle 5
      'baking-section': 9,      // Aisle 6
      'frozen-section': 10,     // Left wall - frozen
      'dairy-section': 11,      // Right wall - dairy
      'health-section': 12,     // Aisle 7 - far back
      'household-section': 13,  // Aisle 8 - far back
      'pet-section': 14         // Far back corner - last
    };
    
    // Sort sections by priority and distance
    while (remainingSections.length > 0) {
      remainingSections.sort((a, b) => {
        const priorityA = sectionPriority[a.svg_element_id] || 99;
        const priorityB = sectionPriority[b.svg_element_id] || 99;
        
        if (priorityA !== priorityB) {
          return priorityA - priorityB;
        }
        
        // If same priority, choose by distance
        const distA = Math.sqrt(Math.pow(currentPosition.x - a.x, 2) + Math.pow(currentPosition.y - a.y, 2));
        const distB = Math.sqrt(Math.pow(currentPosition.x - b.x, 2) + Math.pow(currentPosition.y - b.y, 2));
        return distA - distB;
      });
      
      const nextSection = remainingSections[0];
      optimizedPath.push(nextSection);
      currentPosition = { x: nextSection.x, y: nextSection.y };
      remainingSections = remainingSections.filter(s => s.id !== nextSection.id);
    }
    
    return optimizedPath;
  };
  
  // Enhanced direction generation for complex store
  const generateDirections = (fromSection, toSection, stepNumber, totalSteps) => {
    if (!toSection) return { direction: 'finish', instruction: 'Shopping complete!', icon: Check };
    
    // Entrance to first section
    if (!fromSection) {
      const entranceInstructions = {
        'bakery-section': { direction: 'left', instruction: 'Walk straight from entrance, then turn LEFT to Fresh Bakery', icon: ArrowLeft },
        'produce-section': { direction: 'left', instruction: 'Walk straight ahead to Fresh Produce section on your LEFT', icon: ArrowLeft },
        'deli-section': { direction: 'right', instruction: 'Walk straight from entrance, then turn RIGHT to Deli & Meats', icon: ArrowRight },
        'beverages-section': { direction: 'straight', instruction: 'Walk straight ahead to Aisle 1 - Beverages in center store', icon: ArrowUp },
        'snacks-section': { direction: 'straight', instruction: 'Walk straight ahead to Aisle 2 - Snacks & Chips', icon: ArrowUp }
      };
      
      return entranceInstructions[toSection.svg_element_id] || 
             { direction: 'straight', instruction: `Walk straight ahead to ${toSection.name}`, icon: ArrowUp };
    }
    
    // Calculate direction based on position changes
    const deltaX = toSection.x - fromSection.x;
    const deltaY = toSection.y - fromSection.y;
    
    // Generate contextual instructions based on store layout
    const generateContextualInstruction = () => {
      // Moving between aisles
      if (Math.abs(deltaX) > Math.abs(deltaY)) {
        if (deltaX > 100) {
          return `Turn RIGHT and walk to ${toSection.aisle} - ${toSection.name}`;
        } else if (deltaX < -100) {
          return `Turn LEFT and walk to ${toSection.aisle} - ${toSection.name}`;
        }
      }
      
      // Moving forward/backward in store
      if (Math.abs(deltaY) > Math.abs(deltaX)) {
        if (deltaY > 100) {
          return `Walk toward the FRONT of the store to ${toSection.name}`;
        } else if (deltaY < -100) {
          return `Walk toward the BACK of the store to ${toSection.aisle} - ${toSection.name}`;
        }
      }
      
      // Specific section instructions
      const specificInstructions = {
        'dairy-section': 'Walk to the RIGHT WALL - Dairy section (refrigerated area)',
        'frozen-section': 'Walk to the LEFT WALL - Frozen Foods section (freezer area)',
        'pet-section': 'Walk to the FAR BACK RIGHT CORNER - Pet Supplies',
        'health-section': 'Walk to the FAR BACK - Aisle 7 Health & Beauty',
        'household-section': 'Continue to Aisle 8 - Household & Cleaning supplies'
      };
      
      return specificInstructions[toSection.svg_element_id] || 
             `Continue to ${toSection.aisle} - ${toSection.name}`;
    };
    
    const instruction = generateContextualInstruction();
    
    // Determine icon based on movement
    let icon = ArrowUp;
    if (deltaX > 50) icon = ArrowRight;
    else if (deltaX < -50) icon = ArrowLeft;
    else if (deltaY > 50) icon = ArrowUp;
    
    return {
      direction: deltaX > 0 ? 'right' : deltaX < 0 ? 'left' : 'straight',
      instruction: instruction,
      icon: icon,
      landmark: toSection.landmark,
      aisle: toSection.aisle
    };
  };

  const addToShoppingList = (product) => {
    if (!shoppingList.find(item => item.id === product.id)) {
      setShoppingList([...shoppingList, { ...product, collected: false }]);
    }
  };

  const removeFromShoppingList = (productId) => {
    setShoppingList(shoppingList.filter(item => item.id !== productId));
  };

  const toggleProductCollected = (productId) => {
    setShoppingList(shoppingList.map(item => 
      item.id === productId ? { ...item, collected: !item.collected } : item
    ));
  };

  const startShopping = () => {
    if (shoppingList.length > 0) {
      setShowDirections(true);
      setCurrentStep(0);
      // Highlight first section
      const path = calculateOptimalPath(shoppingList);
      if (path.length > 0) {
        highlightSection(path[0].svg_element_id);
      }
    }
  };

  const nextStep = () => {
    const path = calculateOptimalPath(shoppingList.filter(item => !item.collected));
    if (currentStep < path.length - 1) {
      setCurrentStep(currentStep + 1);
      highlightSection(path[currentStep + 1].svg_element_id);
    } else {
      setShowDirections(false);
      setCurrentStep(0);
      resetHighlight();
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      const path = calculateOptimalPath(shoppingList.filter(item => !item.collected));
      setCurrentStep(currentStep - 1);
      highlightSection(path[currentStep - 1].svg_element_id);
    }
  };

  const highlightSection = (sectionId) => {
    setHighlightedSection(sectionId);
    
    // Reset all sections first
    if (storeData) {
      storeData.sections.forEach(s => {
        const el = document.getElementById(s.svg_element_id);
        if (el) {
          el.style.fill = s.color;
          el.style.opacity = "0.7";
          el.style.stroke = s.color;
          el.style.strokeWidth = "3";
          el.style.filter = "none";
        }
      });
      
      // Highlight selected section
      const element = document.getElementById(sectionId);
      if (element) {
        element.style.fill = "#ffeb3b";
        element.style.opacity = "0.9";
        element.style.stroke = "#f57f17";
        element.style.strokeWidth = "4";
        element.style.filter = "drop-shadow(0 4px 8px rgba(0,0,0,0.3))";
      }
    }
  };

  const handleProductClick = (product) => {
    setSelectedProduct(product);
    
    // Find the section for this product
    const section = storeData.sections.find(s => s.id === product.section_id);
    if (section) {
      highlightSection(section.svg_element_id);
      
      // Scroll to the map
      document.getElementById('store-map')?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const resetHighlight = () => {
    setSelectedProduct(null);
    setHighlightedSection(null);
    
    // Reset all sections to original colors
    if (storeData) {
      storeData.sections.forEach(section => {
        const element = document.getElementById(section.svg_element_id);
        if (element) {
          element.style.fill = section.color;
          element.style.opacity = "0.7";
          element.style.stroke = section.color;
          element.style.strokeWidth = "3";
          element.style.filter = "none";
        }
      });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading store...</p>
        </div>
      </div>
    );
  }

  if (!storeData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Store Not Found</h2>
          <p className="text-gray-600">The requested store could not be found.</p>
          <Button asChild className="mt-4">
            <a href="/">Back to Home</a>
          </Button>
        </div>
      </div>
    );
  }

  // Group products by category
  const productsByCategory = storeData.categories.reduce((acc, category) => {
    acc[category.id] = {
      category,
      products: storeData.products.filter(p => p.category_id === category.id)
    };
    return acc;
  }, {});

  // Calculate optimal path for navigation
  const uncollectedItems = shoppingList.filter(item => !item.collected);
  const optimizedPath = calculateOptimalPath(uncollectedItems);
  const currentSectionData = optimizedPath[currentStep];
  const nextSectionData = optimizedPath[currentStep + 1];
  const directions = generateDirections(currentSectionData, nextSectionData);

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-md border-b sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">{storeData.store.name}</h1>
              <p className="text-gray-600">{storeData.store.address}</p>
            </div>
            <div className="flex gap-2">
              <Badge variant="secondary" className="flex items-center gap-1">
                <ShoppingCart className="h-4 w-4" />
                {shoppingList.length} items
              </Badge>
              <Button asChild variant="outline">
                <a href="/">← Back to Stores</a>
              </Button>
            </div>
          </div>
          
          {/* Search Bar */}
          <div className="mt-4 relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <Input
              type="text"
              placeholder="Search for products..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                handleSearch(e.target.value);
              }}
              className="pl-10"
            />
            
            {/* Search Results */}
            {searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 bg-white border rounded-md shadow-lg mt-1 max-h-60 overflow-y-auto z-20">
                {searchResults.map((product) => (
                  <div
                    key={product.id}
                    className="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                  >
                    <div className="flex justify-between items-center">
                      <div
                        onClick={() => {
                          handleProductClick(product);
                          setSearchQuery("");
                          setSearchResults([]);
                        }}
                        className="flex-1"
                      >
                        <h4 className="font-medium">{product.name}</h4>
                        <p className="text-sm text-gray-600">{product.description}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-emerald-600">${product.price}</p>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={(e) => {
                            e.stopPropagation();
                            addToShoppingList(product);
                            setSearchQuery("");
                            setSearchResults([]);
                          }}
                        >
                          <Plus className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Shopping Navigation */}
      {showDirections && optimizedPath.length > 0 && (
        <div className="bg-blue-600 text-white px-4 py-3">
          <div className="container mx-auto">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  {React.createElement(directions.icon || ArrowUp, { className: "h-6 w-6" })}
                  <span className="font-medium">{directions.instruction}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm">Step {currentStep + 1} of {optimizedPath.length}</span>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={prevStep}
                  disabled={currentStep === 0}
                >
                  ← Back
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={nextStep}
                >
                  {currentStep === optimizedPath.length - 1 ? 'Finish' : 'Next →'}
                </Button>
              </div>
            </div>
            
            {/* Current Section Products */}
            {currentSectionData && (
              <div className="mt-3 p-3 bg-blue-700 rounded-lg">
                <h4 className="font-medium mb-2">Items in {currentSectionData.name}:</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {currentSectionData.products.map((product) => (
                    <div
                      key={product.id}
                      className={`flex items-center justify-between p-2 rounded ${
                        product.collected ? 'bg-green-600' : 'bg-blue-600'
                      }`}
                    >
                      <span className="text-sm">{product.name}</span>
                      <Button
                        size="sm"
                        variant={product.collected ? "secondary" : "outline"}
                        onClick={() => toggleProductCollected(product.id)}
                      >
                        {product.collected ? <Check className="h-4 w-4" /> : 'Collect'}
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="container mx-auto px-4 py-6">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Store Map */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <MapPin className="h-5 w-5" />
                  Store Map
                </CardTitle>
                <div className="flex gap-2">
                  {selectedProduct && !showDirections && (
                    <Button onClick={resetHighlight} variant="outline" size="sm">
                      Clear Selection
                    </Button>
                  )}
                  {shoppingList.length > 0 && !showDirections && (
                    <Button onClick={startShopping} className="bg-blue-600 hover:bg-blue-700">
                      <Navigation className="h-4 w-4 mr-2" />
                      Start Shopping
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div 
                  id="store-map"
                  className="w-full bg-gray-50 rounded-lg p-4 overflow-auto"
                  dangerouslySetInnerHTML={{ __html: storeData.store.layout_svg }}
                />
                
                {selectedProduct && !showDirections && (
                  <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <h4 className="font-semibold text-yellow-800">Selected Product</h4>
                    <p className="text-yellow-700">
                      {selectedProduct.name} - Located in{' '}
                      {storeData.sections.find(s => s.id === selectedProduct.section_id)?.name}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Shopping List & Product Categories */}
          <div className="space-y-4">
            {/* Shopping List */}
            {shoppingList.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2">
                    <ShoppingCart className="h-5 w-5" />
                    Shopping List ({shoppingList.length})
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {shoppingList.map((item) => (
                    <div
                      key={item.id}
                      className={`flex items-center justify-between p-2 rounded-lg border ${
                        item.collected 
                          ? 'bg-green-50 border-green-200 text-green-800' 
                          : 'bg-white border-gray-200'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {item.collected && <Check className="h-4 w-4 text-green-600" />}
                        <div>
                          <p className={`font-medium text-sm ${item.collected ? 'line-through' : ''}`}>
                            {item.name}
                          </p>
                          <p className="text-xs text-gray-500">${item.price}</p>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => removeFromShoppingList(item.id)}
                      >
                        <Minus className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Product Categories */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Package className="h-5 w-5" />
                  Product Categories
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {Object.values(productsByCategory).map(({ category, products }) => (
                  <div key={category.id}>
                    <div className="flex items-center gap-2 mb-2">
                      <div 
                        className="w-4 h-4 rounded-full"
                        style={{ backgroundColor: category.color }}
                      />
                      <h3 className="font-semibold">{category.name}</h3>
                    </div>
                    
                    <div className="space-y-2 ml-6">
                      {products.map((product) => {
                        const inShoppingList = shoppingList.find(item => item.id === product.id);
                        return (
                          <div
                            key={product.id}
                            className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                              selectedProduct?.id === product.id
                                ? 'bg-yellow-50 border-yellow-300 shadow-md'
                                : inShoppingList
                                  ? 'bg-emerald-50 border-emerald-200'
                                  : 'hover:bg-gray-50 border-gray-200'
                            }`}
                          >
                            <div className="flex justify-between items-start">
                              <div
                                className="flex-1"
                                onClick={() => handleProductClick(product)}
                              >
                                <h4 className="font-medium text-sm">{product.name}</h4>
                                <p className="text-xs text-gray-600 mt-1">{product.description}</p>
                              </div>
                              <div className="flex items-center gap-2 ml-2">
                                <Badge variant="secondary" className="text-emerald-600">
                                  ${product.price}
                                </Badge>
                                <Button
                                  size="sm"
                                  variant={inShoppingList ? "destructive" : "outline"}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    if (inShoppingList) {
                                      removeFromShoppingList(product.id);
                                    } else {
                                      addToShoppingList(product);
                                    }
                                  }}
                                >
                                  {inShoppingList ? <Minus className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                                </Button>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/store/:storeId" element={<StorePage />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;