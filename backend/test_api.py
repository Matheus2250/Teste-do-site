"""
Script de teste para as APIs do Espaço VIV
Execute com: python backend/test_api.py
"""
import requests
import json
from datetime import datetime, timedelta

# Configurações
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

# Headers padrão
headers = {
    "Content-Type": "application/json"
}

class APITester:
    def __init__(self):
        self.auth_token = None
        self.headers = headers.copy()
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def test_endpoint(self, method, endpoint, data=None, expected_status=200, auth_required=False):
        """Test a single endpoint"""
        url = f"{API_BASE}{endpoint}"
        
        # Add auth header if required
        test_headers = self.headers.copy()
        if auth_required and self.auth_token:
            test_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=test_headers)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=test_headers)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=test_headers)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=test_headers)
            
            success = response.status_code == expected_status
            status_icon = "✅" if success else "❌"
            
            self.log(f"{status_icon} {method.upper()} {endpoint} -> {response.status_code}")
            
            if not success:
                self.log(f"Expected {expected_status}, got {response.status_code}", "ERROR")
                if response.text:
                    self.log(f"Response: {response.text[:200]}", "ERROR")
            
            return response
            
        except requests.exceptions.ConnectionError:
            self.log(f"❌ {method.upper()} {endpoint} -> CONNECTION ERROR", "ERROR")
            return None
        except Exception as e:
            self.log(f"❌ {method.upper()} {endpoint} -> ERROR: {str(e)}", "ERROR")
            return None
    
    def test_health_check(self):
        """Test basic health endpoints"""
        self.log("=== TESTE DE SAÚDE ===", "INFO")
        
        # Test root endpoint
        self.test_endpoint("GET", "/", expected_status=200)
        
        # Test health endpoint  
        self.test_endpoint("GET", "/health", expected_status=200)
    
    def test_authentication(self):
        """Test authentication endpoints"""
        self.log("=== TESTE DE AUTENTICAÇÃO ===", "INFO")
        
        # Test user registration
        register_data = {
            "name": "João Test Silva",
            "email": "joao.test@espacoviv.com",
            "password": "MinhaSenh@123",
            "cpf": "123.456.789-00",
            "phone": "(11) 99999-9999",
            "unit_preference": "sp-perdizes",
            "specialties": ["Shiatsu", "Relaxante"],
            "experience_years": 5
        }
        
        register_response = self.test_endpoint(
            "POST", "/auth/register", 
            data=register_data, 
            expected_status=200
        )
        
        # Test password strength validation
        self.test_endpoint(
            "POST", "/auth/validate-password",
            data="fraca123",
            expected_status=200
        )
        
        # Test login
        login_data = {
            "email": "joao.test@espacoviv.com",
            "password": "MinhaSenh@123"
        }
        
        login_response = self.test_endpoint(
            "POST", "/auth/login",
            data=login_data,
            expected_status=200
        )
        
        # Extract token for future requests
        if login_response and login_response.status_code == 200:
            try:
                login_json = login_response.json()
                self.auth_token = login_json.get("access_token")
                self.log("✅ Token de autenticação obtido", "INFO")
            except:
                self.log("❌ Falha ao extrair token", "ERROR")
        
        # Test forgot password
        forgot_data = {"email": "joao.test@espacoviv.com"}
        self.test_endpoint(
            "POST", "/auth/forgot-password",
            data=forgot_data,
            expected_status=200
        )
        
        # Test get current user (requires auth)
        self.test_endpoint(
            "GET", "/auth/me",
            auth_required=True,
            expected_status=200
        )
        
        # Test get complete profile
        self.test_endpoint(
            "GET", "/auth/profile/complete",
            auth_required=True,
            expected_status=200
        )
    
    def test_units_and_massagistas(self):
        """Test units and massagistas endpoints"""
        self.log("=== TESTE DE UNIDADES E MASSAGISTAS ===", "INFO")
        
        # Test get all units
        self.test_endpoint("GET", "/units", expected_status=200)
        
        # Test get massagistas by unit
        self.test_endpoint("GET", "/massagista/by-unit/sp-perdizes", expected_status=200)
    
    def test_bookings(self):
        """Test booking endpoints"""
        self.log("=== TESTE DE AGENDAMENTOS ===", "INFO")
        
        # Test create booking
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        booking_data = {
            "client_name": "Maria Test Cliente",
            "client_phone": "(11) 88888-8888",
            "unit_code": "sp-perdizes",
            "massagista_id": 1,
            "service": "Shiatsu",
            "appointment_date": tomorrow,
            "appointment_time": "14:00",
            "notes": "Primeira sessão"
        }
        
        self.test_endpoint(
            "POST", "/bookings",
            data=booking_data,
            expected_status=200
        )
        
        # Test get available times
        self.test_endpoint(
            "GET", f"/bookings/available-times/1/{tomorrow}",
            expected_status=200
        )
        
        # Test get all bookings
        self.test_endpoint("GET", "/bookings", expected_status=200)
    
    def test_calendar(self):
        """Test calendar endpoints"""
        self.log("=== TESTE DE CALENDÁRIO ===", "INFO")
        
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Test day availability
        self.test_endpoint(
            "GET", f"/calendar/availability/day/sp-perdizes/{tomorrow}",
            expected_status=200
        )
        
        # Test week availability  
        monday = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
        self.test_endpoint(
            "GET", f"/calendar/availability/week/sp-perdizes?week_start={monday}",
            expected_status=200
        )
        
        # Test month availability
        current_year = datetime.now().year
        current_month = datetime.now().month
        self.test_endpoint(
            "GET", f"/calendar/availability/month/sp-perdizes/{current_year}/{current_month}",
            expected_status=200
        )
        
        # Test availability stats
        last_month = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        self.test_endpoint(
            "GET", f"/calendar/stats/availability?date_from={last_month}&date_to={today}&unit_code=sp-perdizes",
            expected_status=200
        )
        
        # Test find next available slot
        self.test_endpoint(
            "GET", f"/calendar/next-available/sp-perdizes?from_date={today}",
            expected_status=200
        )
    
    def test_services(self):
        """Test services endpoint"""
        self.log("=== TESTE DE SERVIÇOS ===", "INFO")
        
        self.test_endpoint("GET", "/services", expected_status=200)
    
    def run_all_tests(self):
        """Run all API tests"""
        self.log("🚀 INICIANDO TESTES DAS APIs DO ESPAÇO VIV", "INFO")
        self.log(f"URL base: {API_BASE}", "INFO")
        
        # Check if server is running
        try:
            response = requests.get(BASE_URL)
            if response.status_code != 200:
                self.log("❌ Servidor não está respondendo. Inicie o servidor primeiro.", "ERROR")
                return
        except:
            self.log("❌ Não foi possível conectar ao servidor. Verifique se está rodando.", "ERROR")
            return
        
        # Run tests
        self.test_health_check()
        self.test_authentication()
        self.test_units_and_massagistas()
        self.test_services()
        self.test_bookings()
        self.test_calendar()
        
        self.log("✅ TODOS OS TESTES CONCLUÍDOS!", "INFO")
        
        if self.auth_token:
            self.log("🔑 Use este token para testes manuais:", "INFO")
            self.log(f"Authorization: Bearer {self.auth_token[:50]}...", "INFO")

if __name__ == "__main__":
    print("🧪 ESPAÇO VIV - TESTE DE APIs")
    print("=" * 50)
    
    tester = APITester()
    tester.run_all_tests()
    
    print("\n" + "=" * 50)
    print("📋 RESUMO:")
    print("- Execute o servidor com: python app.py")
    print("- Acesse a documentação em: http://localhost:8000/docs")
    print("- Use este script para verificar se todas as APIs estão funcionando")
    print("- Em caso de erro, verifique os logs do servidor")