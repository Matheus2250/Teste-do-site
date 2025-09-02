/**
 * Controlador de Autenticação do Espaço VIV
 * Gerencia login, cadastro, esqueci senha e validações
 */

class AuthController {
    constructor() {
        this.currentMode = 'login';
        this.passwordStrengthTimer = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadUnits();
        this.setupFormValidations();
    }

    bindEvents() {
        // Navegação entre modos
        document.querySelectorAll('.auth-nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mode = e.target.dataset.mode;
                this.switchMode(mode);
            });
        });

        // Formulários
        document.getElementById('loginFormElement').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        document.getElementById('registerFormElement').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegister();
        });

        document.getElementById('forgotFormElement').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleForgotPassword();
        });

        document.getElementById('resetFormElement').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleResetPassword();
        });

        // Validação de senha em tempo real
        document.getElementById('registerPassword').addEventListener('input', (e) => {
            this.validatePasswordStrength(e.target.value);
        });

        // Formatação de campos
        document.getElementById('registerPhone').addEventListener('input', (e) => {
            e.target.value = APIUtils.formatPhone(e.target.value);
        });

        document.getElementById('registerCPF').addEventListener('input', (e) => {
            e.target.value = APIUtils.formatCPF(e.target.value);
        });

        // Código de reset - apenas números
        document.getElementById('resetToken').addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/\D/g, '').toUpperCase();
        });
    }

    switchMode(mode) {
        // Atualizar navegação
        document.querySelectorAll('.auth-nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });

        // Mostrar formulário correto
        document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.toggle('active', form.id === `${mode}Form`);
        });

        this.currentMode = mode;
        this.clearMessages();
    }

    async loadUnits() {
        try {
            const units = await window.apiService.getUnits();
            const select = document.getElementById('registerUnit');
            
            units.forEach(unit => {
                const option = document.createElement('option');
                option.value = unit.code;
                option.textContent = unit.name;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Erro ao carregar unidades:', error);
        }
    }

    setupFormValidations() {
        // Validação de email em tempo real
        const emailInputs = ['loginEmail', 'registerEmail', 'forgotEmail'];
        emailInputs.forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.addEventListener('blur', () => {
                    if (input.value && !APIUtils.isValidEmail(input.value)) {
                        this.showFieldError(input, 'E-mail inválido');
                    } else {
                        this.clearFieldError(input);
                    }
                });
            }
        });

        // Validação de CPF
        const cpfInput = document.getElementById('registerCPF');
        if (cpfInput) {
            cpfInput.addEventListener('blur', () => {
                const cpf = cpfInput.value.replace(/\D/g, '');
                if (cpf.length > 0 && cpf.length !== 11) {
                    this.showFieldError(cpfInput, 'CPF deve ter 11 dígitos');
                } else {
                    this.clearFieldError(cpfInput);
                }
            });
        }

        // Validação de idade
        const birthDateInput = document.getElementById('registerBirthDate');
        if (birthDateInput) {
            birthDateInput.addEventListener('change', () => {
                const birthDate = new Date(birthDateInput.value);
                const today = new Date();
                const age = Math.floor((today - birthDate) / (365.25 * 24 * 60 * 60 * 1000));
                
                if (age < 18) {
                    this.showFieldError(birthDateInput, 'Idade mínima: 18 anos');
                } else if (age > 80) {
                    this.showFieldError(birthDateInput, 'Idade máxima: 80 anos');
                } else {
                    this.clearFieldError(birthDateInput);
                }
            });
        }
    }

    async validatePasswordStrength(password) {
        if (this.passwordStrengthTimer) {
            clearTimeout(this.passwordStrengthTimer);
        }

        const strengthContainer = document.getElementById('passwordStrength');
        const strengthBar = strengthContainer.querySelector('.strength-fill');
        const strengthText = strengthContainer.querySelector('.strength-text');
        const requirements = strengthContainer.querySelector('.strength-requirements');

        if (!password) {
            strengthText.textContent = 'Digite uma senha';
            strengthBar.style.width = '0%';
            requirements.classList.remove('show');
            return;
        }

        // Mostrar requisitos
        requirements.classList.add('show');

        // Validações locais imediatas
        const checks = {
            length: password.length >= 8,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            number: /\d/.test(password),
            special: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)
        };

        // Atualizar indicadores visuais
        Object.entries(checks).forEach(([requirement, met]) => {
            const element = requirements.querySelector(`[data-requirement="${requirement}"]`);
            if (element) {
                element.classList.toggle('met', met);
            }
        });

        const score = Object.values(checks).filter(Boolean).length;
        const percentage = (score / 5) * 100;
        
        // Cores baseadas no score
        let color = '#dc3545'; // Vermelho
        let text = 'Muito fraca';
        
        if (score >= 2) { color = '#fd7e14'; text = 'Fraca'; }
        if (score >= 3) { color = '#ffc107'; text = 'Regular'; }
        if (score >= 4) { color = '#28a745'; text = 'Boa'; }
        if (score === 5) { color = '#20c997'; text = 'Muito forte'; }

        strengthBar.style.width = `${percentage}%`;
        strengthBar.style.backgroundColor = color;
        strengthText.textContent = text;
        strengthText.style.color = color;

        // Validação no servidor (debounce)
        if (password.length >= 6) {
            this.passwordStrengthTimer = setTimeout(async () => {
                try {
                    const validation = await window.apiService.validatePassword(password);
                    strengthText.textContent = validation.strength;
                } catch (error) {
                    console.warn('Erro na validação de senha:', error);
                }
            }, 500);
        }
    }

    async handleLogin() {
        const btn = document.getElementById('loginBtn');
        this.setButtonLoading(btn, true);
        this.clearMessages();

        try {
            const formData = new FormData(document.getElementById('loginFormElement'));
            const credentials = {
                email: formData.get('email'),
                password: formData.get('password')
            };

            const response = await window.apiService.login(credentials);
            
            this.showMessage(`Bem-vindo, ${response.user.name}! 🎉`, 'success');
            
            // Redirecionar ou fechar modal após 1.5s
            setTimeout(() => {
                this.closeModal();
                window.location.reload(); // Ou redirecionar para dashboard
            }, 1500);

        } catch (error) {
            this.showMessage(`Erro no login: ${error.message}`, 'error');
        } finally {
            this.setButtonLoading(btn, false);
        }
    }

    async handleRegister() {
        const btn = document.getElementById('registerBtn');
        this.setButtonLoading(btn, true);
        this.clearMessages();

        try {
            const form = document.getElementById('registerFormElement');
            const formData = new FormData(form);
            
            // Obter especialidades selecionadas
            const specialties = Array.from(form.querySelectorAll('input[name="specialties"]:checked'))
                .map(checkbox => checkbox.value);

            const userData = {
                name: formData.get('name'),
                email: formData.get('email'),
                password: formData.get('password'),
                cpf: formData.get('cpf') || null,
                phone: formData.get('phone') || null,
                unit_preference: formData.get('unit_preference') || null,
                birth_date: formData.get('birth_date') || null,
                gender: formData.get('gender') || null,
                experience_years: parseInt(formData.get('experience_years')) || null,
                specialties: specialties
            };

            const response = await window.apiService.register(userData);
            
            this.showMessage(
                `Cadastro realizado com sucesso! 🎉\nSua conta foi criada. Faça login para continuar.`, 
                'success'
            );
            
            // Limpar formulário e voltar para login
            form.reset();
            setTimeout(() => {
                this.switchMode('login');
            }, 2000);

        } catch (error) {
            let errorMessage = 'Erro no cadastro';
            
            if (error.message.includes('errors')) {
                try {
                    const errorData = JSON.parse(error.message);
                    if (errorData.errors) {
                        errorMessage = errorData.errors.join('\n');
                    }
                } catch (parseError) {
                    errorMessage = error.message;
                }
            } else {
                errorMessage = error.message;
            }
            
            this.showMessage(errorMessage, 'error');
        } finally {
            this.setButtonLoading(btn, false);
        }
    }

    async handleForgotPassword() {
        const btn = document.getElementById('forgotBtn');
        this.setButtonLoading(btn, true);
        this.clearMessages();

        try {
            const email = document.getElementById('forgotEmail').value;
            
            await window.apiService.forgotPassword(email);
            
            this.showMessage(
                'Código enviado! Verifique seu e-mail e digite o código de 6 dígitos.', 
                'success'
            );
            
            // Ir para a etapa 2
            document.getElementById('forgotStep1').style.display = 'none';
            document.getElementById('forgotStep2').style.display = 'block';

        } catch (error) {
            this.showMessage(`Erro: ${error.message}`, 'error');
        } finally {
            this.setButtonLoading(btn, false);
        }
    }

    async handleResetPassword() {
        const btn = document.getElementById('resetBtn');
        this.setButtonLoading(btn, true);
        this.clearMessages();

        try {
            const token = document.getElementById('resetToken').value;
            const newPassword = document.getElementById('resetPassword').value;
            
            if (token.length !== 6) {
                throw new Error('O código deve ter 6 dígitos');
            }

            await window.apiService.resetPassword(token, newPassword);
            
            this.showMessage(
                'Senha redefinida com sucesso! 🎉\nVocê já pode fazer login com sua nova senha.', 
                'success'
            );
            
            // Voltar para login após 2s
            setTimeout(() => {
                this.resetForgotPassword();
                this.switchMode('login');
            }, 2000);

        } catch (error) {
            this.showMessage(`Erro: ${error.message}`, 'error');
        } finally {
            this.setButtonLoading(btn, false);
        }
    }

    backToForgotStep1() {
        document.getElementById('forgotStep2').style.display = 'none';
        document.getElementById('forgotStep1').style.display = 'block';
        document.getElementById('resetToken').value = '';
        document.getElementById('resetPassword').value = '';
        this.clearMessages();
    }

    resetForgotPassword() {
        document.getElementById('forgotStep2').style.display = 'none';
        document.getElementById('forgotStep1').style.display = 'block';
        document.getElementById('forgotFormElement').reset();
        document.getElementById('resetFormElement').reset();
    }

    setButtonLoading(button, loading) {
        const btnText = button.querySelector('.btn-text');
        const btnLoading = button.querySelector('.btn-loading');
        
        if (loading) {
            btnText.style.display = 'none';
            btnLoading.style.display = 'flex';
            button.disabled = true;
        } else {
            btnText.style.display = 'block';
            btnLoading.style.display = 'none';
            button.disabled = false;
        }
    }

    showMessage(message, type) {
        const messageEl = document.getElementById('authMessage');
        messageEl.textContent = message;
        messageEl.className = `auth-message ${type}`;
        messageEl.style.display = 'block';
        
        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => {
                messageEl.style.display = 'none';
            }, 5000);
        }
    }

    clearMessages() {
        const messageEl = document.getElementById('authMessage');
        messageEl.style.display = 'none';
        messageEl.textContent = '';
        messageEl.className = 'auth-message';
    }

    showFieldError(input, message) {
        this.clearFieldError(input);
        
        const error = document.createElement('div');
        error.className = 'field-error';
        error.textContent = message;
        error.style.cssText = 'color: #dc3545; font-size: 12px; margin-top: 5px;';
        
        input.style.borderColor = '#dc3545';
        input.parentNode.appendChild(error);
    }

    clearFieldError(input) {
        const existingError = input.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        input.style.borderColor = '';
    }

    openModal(mode = 'login') {
        const modal = document.getElementById('authModal');
        modal.style.display = 'block';
        this.switchMode(mode);
    }

    closeModal() {
        const modal = document.getElementById('authModal');
        modal.style.display = 'none';
        this.clearMessages();
        this.resetForms();
    }

    resetForms() {
        document.querySelectorAll('.auth-form form').forEach(form => form.reset());
        this.resetForgotPassword();
        
        // Limpar indicadores de senha
        const strengthBar = document.querySelector('.strength-fill');
        const strengthText = document.querySelector('.strength-text');
        const requirements = document.querySelector('.strength-requirements');
        
        if (strengthBar) strengthBar.style.width = '0%';
        if (strengthText) strengthText.textContent = 'Digite uma senha';
        if (requirements) requirements.classList.remove('show');
    }
}

// ============================================================================
// FUNÇÕES GLOBAIS PARA USO EM HTML
// ============================================================================

function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const button = input.nextElementSibling;
    
    if (input.type === 'password') {
        input.type = 'text';
        button.textContent = '🙈';
    } else {
        input.type = 'password';
        button.textContent = '👁️';
    }
}

function switchAuthMode(mode) {
    window.authController.switchMode(mode);
}

function backToForgotStep1() {
    window.authController.backToForgotStep1();
}

function openAuthModal(mode = 'login') {
    window.authController.openModal(mode);
}

function closeAuthModal() {
    window.authController.closeModal();
}

// ============================================================================
// INICIALIZAÇÃO
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Aguardar API Service estar carregado
    if (window.apiService) {
        window.authController = new AuthController();
        console.log('🔐 Auth Controller carregado!');
    } else {
        setTimeout(() => {
            window.authController = new AuthController();
            console.log('🔐 Auth Controller carregado!');
        }, 100);
    }
});

// Exportar para uso global
window.AuthController = AuthController;