import requests
import sys
import json
from datetime import datetime

class SmartTrolleyAPITester:
    def __init__(self, base_url="https://smart-trolley-app.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.store_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    elif isinstance(response_data, dict):
                        print(f"   Response keys: {list(response_data.keys())}")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            return success, response.json() if response.text and response.status_code < 400 else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test("Root API Endpoint", "GET", "", 200)

    def test_get_stores_empty(self):
        """Test getting stores when database is empty"""
        success, response = self.run_test("Get Stores (Empty)", "GET", "stores", 200)
        if success and isinstance(response, list):
            print(f"   Found {len(response)} stores")
        return success, response

    def test_initialize_sample_data(self):
        """Test initializing sample data"""
        success, response = self.run_test(
            "Initialize Sample Data", 
            "POST", 
            "initialize-sample-data", 
            200
        )
        if success and 'store_id' in response:
            self.store_id = response['store_id']
            print(f"   Sample store created with ID: {self.store_id}")
        return success, response

    def test_get_stores_after_init(self):
        """Test getting stores after initialization"""
        success, response = self.run_test("Get Stores (After Init)", "GET", "stores", 200)
        if success and isinstance(response, list) and len(response) > 0:
            store = response[0]
            expected_fields = ['id', 'name', 'address', 'layout_svg']
            missing_fields = [field for field in expected_fields if field not in store]
            if missing_fields:
                print(f"   ⚠️  Missing fields in store: {missing_fields}")
            else:
                print(f"   Store: {store['name']} at {store['address']}")
        return success, response

    def test_get_store_by_id(self):
        """Test getting a specific store with all data"""
        if not self.store_id:
            print("❌ Skipping - No store ID available")
            return False, {}
        
        success, response = self.run_test(
            "Get Store by ID", 
            "GET", 
            f"stores/{self.store_id}", 
            200
        )
        if success:
            expected_keys = ['store', 'sections', 'categories', 'products']
            missing_keys = [key for key in expected_keys if key not in response]
            if missing_keys:
                print(f"   ⚠️  Missing keys in response: {missing_keys}")
            else:
                print(f"   Store data complete:")
                print(f"     - Sections: {len(response.get('sections', []))}")
                print(f"     - Categories: {len(response.get('categories', []))}")
                print(f"     - Products: {len(response.get('products', []))}")
        return success, response

    def test_search_products(self):
        """Test product search functionality"""
        search_queries = ["chips", "apple", "water", "soap"]
        all_passed = True
        
        for query in search_queries:
            success, response = self.run_test(
                f"Search Products: '{query}'", 
                "GET", 
                f"products/search/{query}", 
                200
            )
            if success:
                print(f"   Found {len(response)} products for '{query}'")
                if response:
                    for product in response[:2]:  # Show first 2 results
                        print(f"     - {product.get('name', 'Unknown')} (${product.get('price', 0)})")
            else:
                all_passed = False
        
        return all_passed, {}

    def test_search_case_insensitive(self):
        """Test case insensitive search"""
        queries = [("CHIPS", "chips"), ("Apple", "apple")]
        all_passed = True
        
        for upper_query, lower_query in queries:
            success1, response1 = self.run_test(
                f"Search (Upper): '{upper_query}'", 
                "GET", 
                f"products/search/{upper_query}", 
                200
            )
            success2, response2 = self.run_test(
                f"Search (Lower): '{lower_query}'", 
                "GET", 
                f"products/search/{lower_query}", 
                200
            )
            
            if success1 and success2:
                if len(response1) == len(response2):
                    print(f"   ✅ Case insensitive search working for '{upper_query}'")
                else:
                    print(f"   ⚠️  Case sensitivity issue: {len(response1)} vs {len(response2)} results")
            else:
                all_passed = False
        
        return all_passed, {}

    def test_invalid_endpoints(self):
        """Test error handling for invalid endpoints"""
        invalid_tests = [
            ("Invalid Store ID", "GET", "stores/invalid-id", 404),
            ("Invalid Product Search", "GET", "products/search/", 404),
        ]
        
        all_passed = True
        for name, method, endpoint, expected_status in invalid_tests:
            success, _ = self.run_test(name, method, endpoint, expected_status)
            if not success:
                all_passed = False
        
        return all_passed, {}

def main():
    print("🚀 Starting Smart Trolley Assistant API Tests")
    print("=" * 60)
    
    tester = SmartTrolleyAPITester()
    
    # Test sequence
    test_results = []
    
    # Basic connectivity
    success, _ = tester.test_root_endpoint()
    test_results.append(("Root API", success))
    
    # Store operations
    success, _ = tester.test_get_stores_empty()
    test_results.append(("Get Stores (Empty)", success))
    
    success, _ = tester.test_initialize_sample_data()
    test_results.append(("Initialize Sample Data", success))
    
    success, _ = tester.test_get_stores_after_init()
    test_results.append(("Get Stores (After Init)", success))
    
    success, _ = tester.test_get_store_by_id()
    test_results.append(("Get Store by ID", success))
    
    # Search functionality
    success, _ = tester.test_search_products()
    test_results.append(("Product Search", success))
    
    success, _ = tester.test_search_case_insensitive()
    test_results.append(("Case Insensitive Search", success))
    
    # Error handling
    success, _ = tester.test_invalid_endpoints()
    test_results.append(("Error Handling", success))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in test_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! Backend API is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the backend implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())