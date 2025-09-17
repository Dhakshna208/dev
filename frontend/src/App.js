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

  // Calculate optimal shopping path
  const calculateOptimalPath = (products) => {
    if (products.length === 0) return [];
    
    // Define section positions (based on our SVG layout)
    const sectionPositions = {
      'fruits-section': { x: 200, y: 150, name: 'FRUITS & VEGETABLES' },
      'snacks-section': { x: 600, y: 150, name: 'SNACKS & CHIPS' },
      'beverages-section': { x: 200, y: 400, name: 'BEVERAGES' },
      'household-section': { x: 600, y: 400, name: 'HOUSEHOLD ITEMS' }
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
    
    // Simple path optimization - start from entrance (bottom) and minimize distance
    const entrance = { x: 400, y: 575 };
    let optimizedPath = [];
    let currentPosition = entrance;
    let remainingSections = [...sectionDetails];
    
    while (remainingSections.length > 0) {
      // Find nearest section
      let nearestSection = remainingSections[0];
      let minDistance = Math.sqrt(Math.pow(currentPosition.x - nearestSection.x, 2) + Math.pow(currentPosition.y - nearestSection.y, 2));
      
      for (let section of remainingSections) {
        const distance = Math.sqrt(Math.pow(currentPosition.x - section.x, 2) + Math.pow(currentPosition.y - section.y, 2));
        if (distance < minDistance) {
          minDistance = distance;
          nearestSection = section;
        }
      }
      
      optimizedPath.push(nearestSection);
      currentPosition = { x: nearestSection.x, y: nearestSection.y };
      remainingSections = remainingSections.filter(s => s.id !== nearestSection.id);
    }
    
    return optimizedPath;
  };
  
  // Generate directions between sections
  const generateDirections = (fromSection, toSection) => {
    if (!fromSection || !toSection) return { direction: 'straight', instruction: 'Continue straight' };
    
    const deltaX = toSection.x - fromSection.x;
    const deltaY = toSection.y - fromSection.y;
    
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      if (deltaX > 0) {
        return { direction: 'right', instruction: `Turn right towards ${toSection.name}`, icon: ArrowRight };
      } else {
        return { direction: 'left', instruction: `Turn left towards ${toSection.name}`, icon: ArrowLeft };
      }
    } else {
      if (deltaY < 0) {
        return { direction: 'straight', instruction: `Go straight to ${toSection.name}`, icon: ArrowUp };
      } else {
        return { direction: 'straight', instruction: `Continue to ${toSection.name}`, icon: ArrowUp };
      }
    }
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
            <Button asChild variant="outline">
              <a href="/">← Back to Stores</a>
            </Button>
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
                    onClick={() => {
                      handleProductClick(product);
                      setSearchQuery("");
                      setSearchResults([]);
                    }}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <h4 className="font-medium">{product.name}</h4>
                        <p className="text-sm text-gray-600">{product.description}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-emerald-600">${product.price}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

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
                {selectedProduct && (
                  <Button onClick={resetHighlight} variant="outline" size="sm">
                    Clear Selection
                  </Button>
                )}
              </CardHeader>
              <CardContent>
                <div 
                  id="store-map"
                  className="w-full bg-gray-50 rounded-lg p-4 overflow-auto"
                  dangerouslySetInnerHTML={{ __html: storeData.store.layout_svg }}
                />
                
                {selectedProduct && (
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

          {/* Product Categories */}
          <div>
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
                      {products.map((product) => (
                        <div
                          key={product.id}
                          className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                            selectedProduct?.id === product.id
                              ? 'bg-yellow-50 border-yellow-300 shadow-md'
                              : 'hover:bg-gray-50 border-gray-200'
                          }`}
                          onClick={() => handleProductClick(product)}
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <h4 className="font-medium text-sm">{product.name}</h4>
                              <p className="text-xs text-gray-600 mt-1">{product.description}</p>
                            </div>
                            <Badge variant="secondary" className="ml-2 text-emerald-600">
                              ${product.price}
                            </Badge>
                          </div>
                        </div>
                      ))}
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