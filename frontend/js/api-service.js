/**
 * Espaço VIV API Service
 * Serviço centralizado para todas as chamadas à API
 */

class APIService {
    constructor() {
        // Detecta se está em produção (Render) ou desenvolvimento
        this.baseURL = window.location.hostname === 'localhost' 
            ? 'http://localhost:10000/api'
            : 'https://site-kzxm.onrender.com/api'; // URL do Render
        
        this.token = localStorage.getItem('espacoviv_token');
        this.headers = {
            'Content-Type': 'application/json'
        };
        
        if (this.token) {
            this.headers.Authorization = `Bearer ${this.token}`;
        }
    }

    // ============================================================================
    // MÉTODOS UTILITÁRIOS
    // ============================================================================

    setAuthToken(token) {
        this.token = token;
        if (token) {
            localStorage.setItem('espacoviv_token', token);
            this.headers.Authorization = `Bearer ${token}`;
        } else {
            localStorage.removeItem('espacoviv_token');
            delete this.headers.Authorization;
        }
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        const config = {
            headers: { ...this.headers },
            ...options
        };

        try {
            console.log(`🌐 API Request: ${config.method || 'GET'} ${url}`);
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ 
                    message: `HTTP Error: ${response.status}` 
                }));
                throw new Error(errorData.message || errorData.detail || 'Erro na API');
            }

            const data = await response.json();
            console.log('✅ API Response:', data);
            return data;
        } catch (error) {
            console.error('❌ API Error:', error);
            throw error;
        }
    }

    // ============================================================================
    // AUTENTICAÇÃO
    // ============================================================================

    /**
     * Registrar novo usuário
     */
    async register(userData) {
        return await this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    }

    /**
     * Fazer login
     */
    async login(credentials) {
        const response = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify(credentials)
        });

        if (response.access_token) {
            this.setAuthToken(response.access_token);
        }

        return response;
    }

    /**
     * Logout
     */
    async logout() {
        try {
            await this.request('/auth/logout', { method: 'POST' });
        } catch (error) {
            console.warn('Erro no logout:', error);
        } finally {
            this.setAuthToken(null);
        }
    }

    /**
     * Solicitar redefinição de senha
     */
    async forgotPassword(email) {
        return await this.request('/auth/forgot-password', {
            method: 'POST',
            body: JSON.stringify({ email })
        });
    }

    /**
     * Redefinir senha com token
     */
    async resetPassword(token, newPassword) {
        return await this.request('/auth/reset-password', {
            method: 'POST',
            body: JSON.stringify({ token, new_password: newPassword })
        });
    }

    /**
     * Alterar senha (logado)
     */
    async changePassword(currentPassword, newPassword) {
        return await this.request('/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({ 
                current_password: currentPassword, 
                new_password: newPassword 
            })
        });
    }

    /**
     * Validar força da senha
     */
    async validatePassword(password) {
        return await this.request('/auth/validate-password', {
            method: 'POST',
            body: JSON.stringify({ password })
        });
    }

    /**
     * Obter dados do usuário logado
     */
    async getCurrentUser() {
        return await this.request('/auth/me');
    }

    /**
     * Obter perfil completo do usuário
     */
    async getCompleteProfile() {
        return await this.request('/auth/profile/complete');
    }

    /**
     * Atualizar perfil do usuário
     */
    async updateProfile(profileData) {
        return await this.request('/auth/profile', {
            method: 'PUT',
            body: JSON.stringify(profileData)
        });
    }

    // ============================================================================
    // UNIDADES E MASSAGISTAS
    // ============================================================================

    /**
     * Obter todas as unidades
     */
    async getUnits() {
        return await this.request('/units');
    }

    /**
     * Obter massagistas por unidade
     */
    async getMassagistasByUnit(unitCode) {
        return await this.request(`/massagista/by-unit/${unitCode}`);
    }

    // ============================================================================
    // AGENDAMENTOS
    // ============================================================================

    /**
     * Criar novo agendamento
     */
    async createBooking(bookingData) {
        return await this.request('/bookings', {
            method: 'POST',
            body: JSON.stringify(bookingData)
        });
    }

    /**
     * Obter horários disponíveis para um massagista em uma data
     */
    async getAvailableTimes(massagistaId, date) {
        return await this.request(`/bookings/available-times/${massagistaId}/${date}`);
    }

    /**
     * Obter todos os agendamentos (com filtros opcionais)
     */
    async getBookings(filters = {}) {
        const params = new URLSearchParams();
        
        Object.entries(filters).forEach(([key, value]) => {
            if (value) params.append(key, value);
        });

        const queryString = params.toString();
        const endpoint = queryString ? `/bookings?${queryString}` : '/bookings';
        
        return await this.request(endpoint);
    }

    /**
     * Obter agendamento por ID
     */
    async getBooking(bookingId) {
        return await this.request(`/bookings/${bookingId}`);
    }

    /**
     * Atualizar status do agendamento
     */
    async updateBookingStatus(bookingId, status) {
        return await this.request(`/bookings/${bookingId}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status })
        });
    }

    // ============================================================================
    // CALENDÁRIO INTELIGENTE
    // ============================================================================

    /**
     * Obter disponibilidade detalhada de um dia
     */
    async getDayAvailability(unitCode, date, massagistaId = null) {
        let endpoint = `/calendar/availability/day/${unitCode}/${date}`;
        if (massagistaId) {
            endpoint += `?massagista_id=${massagistaId}`;
        }
        return await this.request(endpoint);
    }

    /**
     * Obter disponibilidade de uma semana
     */
    async getWeekAvailability(unitCode, weekStart) {
        return await this.request(`/calendar/availability/week/${unitCode}?week_start=${weekStart}`);
    }

    /**
     * Obter disponibilidade de um mês
     */
    async getMonthAvailability(unitCode, year, month) {
        return await this.request(`/calendar/availability/month/${unitCode}/${year}/${month}`);
    }

    /**
     * Obter estatísticas de disponibilidade
     */
    async getAvailabilityStats(filters = {}) {
        const params = new URLSearchParams();
        
        Object.entries(filters).forEach(([key, value]) => {
            if (value) params.append(key, value);
        });

        return await this.request(`/calendar/stats/availability?${params.toString()}`);
    }

    /**
     * Encontrar próximo slot disponível
     */
    async getNextAvailableSlot(unitCode, fromDate = null) {
        let endpoint = `/calendar/next-available/${unitCode}`;
        if (fromDate) {
            endpoint += `?from_date=${fromDate}`;
        }
        return await this.request(endpoint);
    }

    // ============================================================================
    // SERVIÇOS
    // ============================================================================

    /**
     * Obter todos os serviços disponíveis
     */
    async getServices() {
        return await this.request('/services');
    }

    // ============================================================================
    // HEALTH CHECK
    // ============================================================================

    /**
     * Verificar saúde da API
     */
    async healthCheck() {
        return await this.request('/health');
    }

    /**
     * Verificar se API está funcionando
     */
    async isAPIOnline() {
        try {
            await this.request('/');
            return true;
        } catch (error) {
            console.error('API não está respondendo:', error);
            return false;
        }
    }
}

// ============================================================================
// UTILITÁRIOS DE FORMATAÇÃO E VALIDAÇÃO
// ============================================================================

class APIUtils {
    /**
     * Formatar data para envio à API (YYYY-MM-DD)
     */
    static formatDateForAPI(date) {
        if (date instanceof Date) {
            return date.toISOString().split('T')[0];
        }
        return date;
    }

    /**
     * Formatar telefone brasileiro
     */
    static formatPhone(phone) {
        return phone.replace(/\D/g, '').replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
    }

    /**
     * Formatar CPF brasileiro
     */
    static formatCPF(cpf) {
        return cpf.replace(/\D/g, '').replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
    }

    /**
     * Validar formato de email
     */
    static isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    /**
     * Obter início da semana (segunda-feira)
     */
    static getWeekStart(date = new Date()) {
        const d = new Date(date);
        const day = d.getDay();
        const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Ajusta para segunda-feira
        return new Date(d.setDate(diff));
    }

    /**
     * Formatar data para exibição brasileira
     */
    static formatDateBR(date) {
        if (typeof date === 'string') {
            date = new Date(date);
        }
        return date.toLocaleDateString('pt-BR');
    }

    /**
     * Formatar data e hora para exibição
     */
    static formatDateTime(date) {
        if (typeof date === 'string') {
            date = new Date(date);
        }
        return date.toLocaleString('pt-BR');
    }
}

// ============================================================================
// EXPORTAR PARA USO GLOBAL
// ============================================================================

// Instância global do serviço API
window.apiService = new APIService();
window.APIUtils = APIUtils;

console.log('🚀 Espaço VIV API Service carregado!');
console.log('📡 Base URL:', window.apiService.baseURL);