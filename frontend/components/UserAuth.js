class UserAuth {
    constructor() {
        this.currentUser = null;
        this.init();
    }
    
    init() {
        this.loadCurrentUser();
        this.bindEvents();
        this.updateUI();
    }
    
    bindEvents() {
        // Login form
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }
        
        // Register form
        const registerForm = document.getElementById('registerForm');
        if (registerForm) {
            registerForm.addEventListener('submit', (e) => this.handleRegister(e));
        }
        
        // Toggle forms
        const showRegisterForm = document.getElementById('showRegisterForm');
        const showLoginForm = document.getElementById('showLoginForm');
        
        if (showRegisterForm) {
            showRegisterForm.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleForms('register');
            });
        }
        
        if (showLoginForm) {
            showLoginForm.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleForms('login');
            });
        }
        
        // Login button
        const loginBtn = document.getElementById('loginBtn');
        if (loginBtn) {
            loginBtn.addEventListener('click', () => {
                document.getElementById('loginModal').style.display = 'block';
            });
        }
        
        // Logout
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }
        
        // User menu toggle
        const userMenuToggle = document.getElementById('userMenuToggle');
        if (userMenuToggle) {
            userMenuToggle.addEventListener('click', () => this.toggleUserMenu());
        }
        
        // Dashboard link
        const dashboardLink = document.getElementById('dashboardLink');
        if (dashboardLink) {
            dashboardLink.addEventListener('click', () => {
                window.location.href = 'dashboard.html';
            });
        }
        
        // Input masks
        this.setupInputMasks();
    }
    
    setupInputMasks() {
        const cpfInput = document.getElementById('registerCpf');
        const phoneInput = document.getElementById('registerPhone');
        
        if (cpfInput) {
            cpfInput.addEventListener('input', (e) => {
                let value = e.target.value.replace(/\D/g, '');
                value = value.replace(/(\d{3})(\d)/, '$1.$2');
                value = value.replace(/(\d{3})(\d)/, '$1.$2');
                value = value.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
                e.target.value = value;
            });
        }
        
        if (phoneInput) {
            phoneInput.addEventListener('input', (e) => {
                let value = e.target.value.replace(/\D/g, '');
                value = value.replace(/(\d{2})(\d)/, '($1) $2');
                value = value.replace(/(\d{5})(\d)/, '$1-$2');
                e.target.value = value;
            });
        }
    }
    
    toggleForms(formType) {
        const loginDiv = document.getElementById('loginFormDiv');
        const registerDiv = document.getElementById('registerFormDiv');
        
        if (formType === 'register') {
            loginDiv.style.display = 'none';
            registerDiv.style.display = 'block';
        } else {
            loginDiv.style.display = 'block';
            registerDiv.style.display = 'none';
        }
    }
    
    async handleLogin(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        
        const btnText = document.querySelector('#loginForm .btn-text');
        const btnLoading = document.querySelector('#loginForm .btn-loading');
        
        this.toggleLoadingState(btnText, btnLoading, true);
        
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: formData.get('loginEmail'),
                    password: formData.get('loginPassword')
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.setCurrentUser(data.user);
                this.closeLoginModal();
                alert('Login realizado com sucesso!');
            } else {
                alert(data.message || 'Erro no login');
            }
        } catch (error) {
            alert('Erro de conexão. Tente novamente.');
        } finally {
            this.toggleLoadingState(btnText, btnLoading, false);
        }
    }
    
    async handleRegister(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        
        const btnText = document.querySelector('#registerForm .btn-text');
        const btnLoading = document.querySelector('#registerForm .btn-loading');
        
        this.toggleLoadingState(btnText, btnLoading, true);
        
        try {
            const specialties = Array.from(document.querySelectorAll('input[name="specialties"]:checked'))
                .map(checkbox => checkbox.value);
            
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: formData.get('registerName'),
                    email: formData.get('registerEmail'),
                    password: formData.get('registerPassword'),
                    cpf: formData.get('registerCpf'),
                    phone: formData.get('registerPhone'),
                    unit_preference: formData.get('unitPreference'),
                    specialties: specialties
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                alert('Cadastro realizado com sucesso! Faça o login para continuar.');
                this.toggleForms('login');
            } else {
                alert(data.message || 'Erro no cadastro');
            }
        } catch (error) {
            alert('Erro de conexão. Tente novamente.');
        } finally {
            this.toggleLoadingState(btnText, btnLoading, false);
        }
    }
    
    toggleLoadingState(btnText, btnLoading, loading) {
        if (btnText && btnLoading) {
            btnText.style.display = loading ? 'none' : 'inline';
            btnLoading.style.display = loading ? 'inline' : 'none';
        }
    }
    
    setCurrentUser(user) {
        this.currentUser = user;
        localStorage.setItem('espacoviv_current_user', JSON.stringify(user));
        this.updateUI();
    }
    
    loadCurrentUser() {
        const stored = localStorage.getItem('espacoviv_current_user');
        if (stored) {
            this.currentUser = JSON.parse(stored);
        }
    }
    
    logout() {
        this.currentUser = null;
        localStorage.removeItem('espacoviv_current_user');
        this.updateUI();
        window.location.href = 'index.html';
    }
    
    updateUI() {
        const loginBtn = document.getElementById('loginBtn');
        const userMenu = document.getElementById('userMenu');
        const userName = document.getElementById('userName');
        
        if (this.currentUser) {
            if (loginBtn) loginBtn.style.display = 'none';
            if (userMenu) userMenu.style.display = 'block';
            if (userName) userName.textContent = this.currentUser.name;
        } else {
            if (loginBtn) loginBtn.style.display = 'block';
            if (userMenu) userMenu.style.display = 'none';
        }
    }
    
    toggleUserMenu() {
        const dropdown = document.getElementById('userDropdown');
        if (dropdown) {
            const isVisible = dropdown.style.display === 'block';
            dropdown.style.display = isVisible ? 'none' : 'block';
        }
    }
    
    closeLoginModal() {
        const modal = document.getElementById('loginModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    isLoggedIn() {
        return this.currentUser !== null;
    }
    
    getCurrentUser() {
        return this.currentUser;
    }
}

// Global instance
const userAuth = new UserAuth();

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    const userMenu = document.getElementById('userMenu');
    const dropdown = document.getElementById('userDropdown');
    
    if (userMenu && dropdown && !userMenu.contains(e.target)) {
        dropdown.style.display = 'none';
    }
});