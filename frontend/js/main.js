// API Service Integration
class APIService {
    constructor() {
        this.baseURL = window.location.hostname === 'localhost' 
            ? 'http://localhost:10000/api'
            : 'https://site-kzxm.onrender.com/api';
        
        this.token = localStorage.getItem('espacoviv_token');
        this.headers = { 'Content-Type': 'application/json' };
        
        if (this.token) {
            this.headers.Authorization = `Bearer ${this.token}`;
        }
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = { headers: { ...this.headers }, ...options };

        try {
            const response = await fetch(url, config);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ 
                    message: `HTTP Error: ${response.status}` 
                }));
                throw new Error(errorData.message || errorData.detail || 'Erro na API');
            }
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // Auth methods
    async register(userData) {
        return await this.request('/auth/register', {
            method: 'POST', body: JSON.stringify(userData)
        });
    }

    async login(credentials) {
        const response = await this.request('/auth/login', {
            method: 'POST', body: JSON.stringify(credentials)
        });
        if (response.access_token) {
            this.token = response.access_token;
            localStorage.setItem('espacoviv_token', this.token);
            this.headers.Authorization = `Bearer ${this.token}`;
        }
        return response;
    }

    async validatePassword(password) {
        return await this.request('/auth/validate-password', {
            method: 'POST', body: JSON.stringify({ password })
        });
    }

    async getUnits() {
        return await this.request('/units');
    }

    async getServices() {
        return await this.request('/services');
    }

    async getDayAvailability(unitCode, date) {
        return await this.request(`/calendar/availability/day/${unitCode}/${date}`);
    }

    async getNextAvailableSlot(unitCode) {
        return await this.request(`/calendar/next-available/${unitCode}`);
    }

    async createBooking(bookingData) {
        return await this.request('/bookings', {
            method: 'POST', body: JSON.stringify(bookingData)
        });
    }
}

// Main application initialization
class EspacoVivApp {
    constructor() {
        this.api = new APIService();
        this.init();
    }
    
    init() {
        this.initializeSwiper();
        this.bindGlobalEvents();
        this.loadComponents();
    }
    
    initializeSwiper() {
        // Initialize Swiper for hero section
        if (document.querySelector('.heroSwiper')) {
            const swiper = new Swiper('.heroSwiper', {
                loop: true,
                autoplay: {
                    delay: 5000,
                    disableOnInteraction: false,
                },
                effect: 'fade',
                fadeEffect: {
                    crossFade: true
                },
                navigation: {
                    nextEl: '.swiper-button-next',
                    prevEl: '.swiper-button-prev',
                },
            });
        }
    }
    
    bindGlobalEvents() {
        // Modal close events
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-close')) {
                const modal = e.target.closest('.modal');
                if (modal) {
                    modal.style.display = 'none';
                }
            }
            
            if (e.target.classList.contains('modal')) {
                e.target.style.display = 'none';
            }
        });
        
        // Agendamento button
        const agendarBtn = document.getElementById('agendarBtn');
        if (agendarBtn) {
            agendarBtn.addEventListener('click', () => {
                if (typeof bookingModal !== 'undefined') {
                    bookingModal.openModal();
                }
            });
        }
        
        // Form submissions
        this.bindFormSubmissions();
    }
    
    bindFormSubmissions() {
        // Booking form
        const agendamentoForm = document.getElementById('agendamentoForm');
        if (agendamentoForm) {
            agendamentoForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                if (typeof bookingModal !== 'undefined') {
                    const formData = new FormData(e.target);
                    const success = await bookingModal.submitBooking(formData);
                    
                    if (success) {
                        e.target.reset();
                    }
                }
            });
        }
    }
    
    loadComponents() {
        // Load required components based on page
        const currentPage = this.getCurrentPage();
        
        switch (currentPage) {
            case 'dashboard':
                this.loadDashboardComponents();
                break;
            case 'promocoes':
                this.loadPromocaoComponents();
                break;
            default:
                // Default components for all pages
                break;
        }
    }
    
    getCurrentPage() {
        const path = window.location.pathname;
        const page = path.split('/').pop().replace('.html', '');
        return page || 'index';
    }
    
    loadDashboardComponents() {
        // Dashboard specific initialization
        if (typeof userAuth !== 'undefined' && !userAuth.isLoggedIn()) {
            window.location.href = 'index.html';
            return;
        }
        
        this.initializeDashboard();
    }
    
    loadPromocaoComponents() {
        // Promocoes specific initialization
        this.bindPromocaoEvents();
    }
    
    bindPromocaoEvents() {
        // Promocao buttons
        document.querySelectorAll('.promocao-action').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const promocaoTitle = button.closest('.promocao-card').querySelector('h3').textContent;
                if (typeof bookingModal !== 'undefined') {
                    bookingModal.openModal(promocaoTitle);
                }
            });
        });
    }
    
    initializeDashboard() {
        this.loadCalendar();
        this.loadAppointments();
        this.bindDashboardEvents();
    }
    
    async loadCalendar() {
        const calendarContainer = document.getElementById('calendar-container');
        if (!calendarContainer) return;
        
        try {
            const response = await fetch('/api/massagista/appointments/calendar');
            const appointments = await response.json();
            
            this.renderCalendar(appointments);
        } catch (error) {
            console.error('Erro ao carregar calendário:', error);
        }
    }
    
    async loadAppointments() {
        const appointmentsList = document.getElementById('appointments-list');
        if (!appointmentsList) return;
        
        try {
            const response = await fetch('/api/massagista/appointments');
            const appointments = await response.json();
            
            this.renderAppointments(appointments);
        } catch (error) {
            console.error('Erro ao carregar agendamentos:', error);
        }
    }
    
    renderCalendar(appointments) {
        const calendarContainer = document.getElementById('calendar-container');
        const today = new Date();
        const currentMonth = today.getMonth();
        const currentYear = today.getFullYear();
        
        // Simple calendar implementation
        const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
        let calendarHTML = '<div class="calendar-grid">';
        
        // Header
        calendarHTML += '<div class="calendar-header">';
        calendarHTML += `<h3>${this.getMonthName(currentMonth)} ${currentYear}</h3>`;
        calendarHTML += '</div>';
        
        // Days of week
        const daysOfWeek = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
        calendarHTML += '<div class="calendar-days-header">';
        daysOfWeek.forEach(day => {
            calendarHTML += `<div class="calendar-day-header">${day}</div>`;
        });
        calendarHTML += '</div>';
        
        // Calendar days
        calendarHTML += '<div class="calendar-days">';
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(currentYear, currentMonth, day);
            const dateStr = date.toISOString().split('T')[0];
            const dayAppointments = appointments.filter(apt => apt.appointment_date === dateStr);
            
            calendarHTML += `<div class="calendar-day ${dayAppointments.length > 0 ? 'has-appointments' : ''}" data-date="${dateStr}">`;
            calendarHTML += `<span class="day-number">${day}</span>`;
            if (dayAppointments.length > 0) {
                calendarHTML += `<span class="appointment-count">${dayAppointments.length}</span>`;
            }
            calendarHTML += '</div>';
        }
        calendarHTML += '</div></div>';
        
        calendarContainer.innerHTML = calendarHTML;
    }
    
    renderAppointments(appointments) {
        const appointmentsList = document.getElementById('appointments-list');
        
        if (appointments.length === 0) {
            appointmentsList.innerHTML = '<p>Nenhum agendamento encontrado.</p>';
            return;
        }
        
        let appointmentsHTML = '';
        appointments.forEach(appointment => {
            const date = new Date(appointment.appointment_date).toLocaleDateString('pt-BR');
            const status = this.getStatusBadge(appointment.status);
            
            appointmentsHTML += `
                <div class="appointment-card" data-id="${appointment.id}">
                    <div class="appointment-header">
                        <h4>${appointment.client_name}</h4>
                        ${status}
                    </div>
                    <div class="appointment-details">
                        <p><i class="fas fa-calendar"></i> ${date} às ${appointment.appointment_time}</p>
                        <p><i class="fas fa-spa"></i> ${appointment.service}</p>
                        <p><i class="fas fa-phone"></i> ${appointment.phone}</p>
                        ${appointment.notes ? `<p><i class="fas fa-comment"></i> ${appointment.notes}</p>` : ''}
                    </div>
                    <div class="appointment-actions">
                        <button onclick="espacoVivApp.updateAppointmentStatus(${appointment.id}, 'confirmed')" class="btn-confirm">Confirmar</button>
                        <button onclick="espacoVivApp.updateAppointmentStatus(${appointment.id}, 'cancelled')" class="btn-cancel">Cancelar</button>
                    </div>
                </div>
            `;
        });
        
        appointmentsList.innerHTML = appointmentsHTML;
    }
    
    getStatusBadge(status) {
        const statusMap = {
            'pending': { text: 'Pendente', class: 'status-pending' },
            'confirmed': { text: 'Confirmado', class: 'status-confirmed' },
            'cancelled': { text: 'Cancelado', class: 'status-cancelled' },
            'completed': { text: 'Concluído', class: 'status-completed' }
        };
        
        const statusInfo = statusMap[status] || { text: 'Desconhecido', class: 'status-unknown' };
        return `<span class="status-badge ${statusInfo.class}">${statusInfo.text}</span>`;
    }
    
    async updateAppointmentStatus(appointmentId, status) {
        try {
            const response = await fetch(`/api/massagista/appointments/${appointmentId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status })
            });
            
            if (response.ok) {
                this.loadAppointments(); // Reload appointments
                alert('Status atualizado com sucesso!');
            } else {
                throw new Error('Erro ao atualizar status');
            }
        } catch (error) {
            alert('Erro ao atualizar status. Tente novamente.');
        }
    }
    
    bindDashboardEvents() {
        // Calendar day click
        document.addEventListener('click', (e) => {
            if (e.target.closest('.calendar-day')) {
                const day = e.target.closest('.calendar-day');
                const date = day.dataset.date;
                this.showDayAppointments(date);
            }
        });
    }
    
    showDayAppointments(date) {
        // Implementation for showing day appointments
        console.log('Showing appointments for date:', date);
    }
    
    getMonthName(monthIndex) {
        const months = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ];
        return months[monthIndex];
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.espacoVivApp = new EspacoVivApp();
});
    
    EspacoVIV.initSwiper = function() {
        // Inicializar Swiper para o slider hero
        this.swiper = new Swiper('.elementor-main-swiper', {
            loop: true,
            autoplay: {
                delay: 5000,
                disableOnInteraction: false,
            },
            effect: 'fade',
            fadeEffect: {
                crossFade: true
            },
            navigation: {
                nextEl: '.elementor-swiper-button-next',
                prevEl: '.elementor-swiper-button-prev',
            },
            on: {
                slideChangeTransitionStart: function() {
                    // Adicionar animações aos slides
                    $('.swiper-slide-active .elementor-slide-heading').addClass('fadeInDown');
                    $('.swiper-slide-active .elementor-slide-description').addClass('fadeInUp');
                    $('.swiper-slide-active .elementor-slide-button').addClass('fadeInUp');
                }
            }
        });
    };
    
    EspacoVIV.initHeader = function() {
        // Header sticky
        $(window).on('scroll', function() {
            var $header = $('#header');
            if ($(window).scrollTop() > 100) {
                $header.addClass('sticky');
            } else {
                $header.removeClass('sticky');
            }
        });
        
        // Mobile menu toggle
        $('.mobile-menu-toggle').on('click', function() {
            $(this).toggleClass('active');
            $('.main-nav').toggleClass('mobile-open');
        });
    };
    
    EspacoVIV.initForms = function() {
        // Formulário de newsletter
        $('#leadForm').on('submit', function(e) {
            e.preventDefault();
            EspacoVIV.handleNewsletterSubmit($(this));
        });
        
        // Formulário de newsletter no footer
        $('.newsletter-form').on('submit', function(e) {
            e.preventDefault();
            EspacoVIV.handleNewsletterSubmit($(this));
        });
    };
    
    EspacoVIV.initMasks = function() {
        // Máscaras para telefone (se jQuery Mask estiver disponível)
        if ($.fn.mask) {
            $('input[type="tel"]').mask('(00) 00000-0000');
        }
    };
    
    EspacoVIV.initModals = function() {
        // Fechar modal ao clicar no X ou fora do modal
        $('.modal .close').on('click', function() {
            $(this).closest('.modal').hide();
        });
        
        $(window).on('click', function(e) {
            if ($(e.target).hasClass('modal')) {
                $('.modal').hide();
            }
        });
        
        // ESC para fechar modais
        $(document).on('keyup', function(e) {
            if (e.keyCode === 27) { // ESC
                $('.modal').hide();
            }
        });
    };
    
    EspacoVIV.initSmoothScroll = function() {
        // Scroll suave para links de âncora
        $('a[href^="#"]').on('click', function(e) {
            var target = $(this.getAttribute('href'));
            if (target.length) {
                e.preventDefault();
                $('html, body').animate({
                    scrollTop: target.offset().top - 80
                }, 800);
            }
        });
    };
    
    EspacoVIV.bindEvents = function() {
        // Botão de login das massagistas
        $('#loginBtn').on('click', function() {
            EspacoVIV.openLoginModal();
        });
        
        // Botão de agendamento
        $('#agendarBtn').on('click', function() {
            EspacoVIV.openBookingModal();
        });
        
        // Links de promoções
        $('.btn:contains("Quero Participar"), .btn:contains("Saiba Mais")').on('click', function() {
            EspacoVIV.showMessage('Entre em contato conosco para mais informações sobre esta promoção!', 'info');
        });
    };
    
    EspacoVIV.openLoginModal = function() {
        $('#loginModalBody').html(EspacoVIV.getLoginFormHTML());
        $('#loginModal').show();
        
        // Bind eventos específicos do login
        EspacoVIV.bindLoginEvents();
    };
    
    EspacoVIV.openBookingModal = function() {
        $('#bookingModalBody').html(EspacoVIV.getBookingFormHTML());
        $('#bookingModal').show();
        
        // Bind eventos específicos do agendamento
        EspacoVIV.bindBookingEvents();
        
        // Inicializar data mínima
        var today = new Date().toISOString().split('T')[0];
        $('#bookingDate').attr('min', today);
    };
    
    EspacoVIV.getLoginFormHTML = function() {
        return `
            <form id="massagistLoginForm" class="login-form">
                <div class="form-group">
                    <label for="loginEmail">E-mail:</label>
                    <input type="email" id="loginEmail" name="email" class="form-control" required>
                </div>
                <div class="form-group">
                    <label for="loginPassword">Senha:</label>
                    <input type="password" id="loginPassword" name="password" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-primary full-width">
                    <span class="btn-text">Entrar</span>
                    <span class="btn-loading" style="display: none;"><i class="fas fa-spinner fa-spin"></i> Entrando...</span>
                </button>
                <div class="login-links">
                    <a href="#" id="showForgotPassword">Esqueci minha senha</a>
                    <a href="#" id="showRegister">Cadastre-se</a>
                </div>
            </form>
            
            <form id="massagistRegisterForm" class="login-form" style="display: none;">
                <div class="form-group">
                    <label for="regName">Nome Completo:</label>
                    <input type="text" id="regName" name="name" class="form-control" required>
                </div>
                <div class="form-group">
                    <label for="regEmail">E-mail:</label>
                    <input type="email" id="regEmail" name="email" class="form-control" required>
                </div>
                <div class="form-group">
                    <label for="regPassword">Senha:</label>
                    <input type="password" id="regPassword" name="password" class="form-control" required minlength="6">
                </div>
                <div class="form-group">
                    <label for="regPhone">Telefone:</label>
                    <input type="tel" id="regPhone" name="phone" class="form-control">
                </div>
                <div class="form-group">
                    <label for="regUnit">Unidade:</label>
                    <select id="regUnit" name="unit" class="form-control" required>
                        <option value="">Selecione uma unidade</option>
                        <option value="sp">São Paulo - Perdizes</option>
                        <option value="rj">Rio de Janeiro - Centro</option>
                        <option value="bsb">Brasília - SHS</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="regMassageTypes">Tipos de Massagem:</label>
                    <textarea id="regMassageTypes" name="massage_types" class="form-control" rows="3" placeholder="Ex: Shiatsu, Relaxante, Terapêutica"></textarea>
                </div>
                <button type="submit" class="btn btn-primary full-width">
                    <span class="btn-text">Cadastrar</span>
                    <span class="btn-loading" style="display: none;"><i class="fas fa-spinner fa-spin"></i> Cadastrando...</span>
                </button>
                <div class="login-links">
                    <a href="#" id="backToLogin">Voltar ao Login</a>
                </div>
            </form>
            
            <div id="loginMessage" class="message" style="display: none;"></div>
        `;
    };
    
    EspacoVIV.getBookingFormHTML = function() {
        return `
            <form id="clientBookingForm" class="booking-form">
                <div class="form-row">
                    <div class="form-group">
                        <label for="clientName">Nome Completo:</label>
                        <input type="text" id="clientName" name="name" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label for="clientEmail">E-mail (opcional):</label>
                        <input type="email" id="clientEmail" name="email" class="form-control">
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="clientPhone">Telefone:</label>
                        <input type="tel" id="clientPhone" name="phone" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label for="bookingUnit">Unidade:</label>
                        <select id="bookingUnit" name="unit" class="form-control" required>
                            <option value="">Selecione uma unidade</option>
                            <option value="sp">São Paulo - Perdizes</option>
                            <option value="rj">Rio de Janeiro - Centro</option>
                            <option value="bsb">Brasília - SHS</option>
                        </select>
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="bookingMassageType">Tipo de Massagem:</label>
                        <select id="bookingMassageType" name="massage_type" class="form-control" required>
                            <option value="">Selecione o tipo</option>
                            <option value="shiatsu" data-duration="60" data-price="120">Shiatsu (60 min) - R$ 120,00</option>
                            <option value="quick" data-duration="15" data-price="40">Quick Massage (15 min) - R$ 40,00</option>
                            <option value="relaxante" data-duration="60" data-price="100">Relaxante (60 min) - R$ 100,00</option>
                            <option value="terapeutica" data-duration="75" data-price="150">Terapêutica (75 min) - R$ 150,00</option>
                            <option value="reflexologia" data-duration="45" data-price="80">Reflexologia (45 min) - R$ 80,00</option>
                            <option value="drenagem" data-duration="60" data-price="130">Drenagem Linfática (60 min) - R$ 130,00</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="bookingDate">Data Desejada:</label>
                        <input type="date" id="bookingDate" name="date" class="form-control" required>
                    </div>
                </div>
                
                <div id="massagistSelection" class="form-section" style="display: none;">
                    <label>Massagistas Disponíveis:</label>
                    <div id="massagistList" class="massagist-grid">
                        <!-- Massagistas serão carregadas aqui -->
                    </div>
                </div>
                
                <div id="timeSelection" class="form-section" style="display: none;">
                    <label>Horários Disponíveis:</label>
                    <div id="timeSlots" class="time-grid">
                        <!-- Horários serão carregados aqui -->
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="bookingNotes">Observações (opcional):</label>
                    <textarea id="bookingNotes" name="notes" class="form-control" rows="2" placeholder="Alguma observação especial?"></textarea>
                </div>
                
                <button type="submit" class="btn btn-primary full-width" disabled>
                    <span class="btn-text">Confirmar Agendamento</span>
                    <span class="btn-loading" style="display: none;"><i class="fas fa-spinner fa-spin"></i> Agendando...</span>
                </button>
            </form>
            
            <div id="bookingSuccess" class="booking-success" style="display: none;">
                <div class="success-icon">
                    <i class="fas fa-check-circle"></i>
                </div>
                <h3>Agendamento Confirmado!</h3>
                <div id="bookingDetails" class="booking-details"></div>
                <button class="btn btn-primary" onclick="location.reload()">
                    <i class="fas fa-plus"></i> Novo Agendamento
                </button>
            </div>
            
            <div id="bookingMessage" class="message" style="display: none;"></div>
        `;
    };
    
    EspacoVIV.bindLoginEvents = function() {
        // Alternar entre formulários
        $('#showRegister').on('click', function(e) {
            e.preventDefault();
            $('#massagistLoginForm').hide();
            $('#massagistRegisterForm').show();
        });
        
        $('#backToLogin, #showForgotPassword').on('click', function(e) {
            e.preventDefault();
            $('#massagistRegisterForm').hide();
            $('#massagistLoginForm').show();
        });
        
        // Submit login
        $('#massagistLoginForm').on('submit', function(e) {
            e.preventDefault();
            EspacoVIV.handleLogin();
        });
        
        // Submit registro
        $('#massagistRegisterForm').on('submit', function(e) {
            e.preventDefault();
            EspacoVIV.handleRegister();
        });
        
        // Máscara para telefone
        if ($.fn.mask) {
            $('#regPhone').mask('(00) 00000-0000');
        }
    };
    
    EspacoVIV.bindBookingEvents = function() {
        // Mudanças que podem afetar disponibilidade
        $('#bookingUnit, #bookingMassageType, #bookingDate').on('change', function() {
            EspacoVIV.updateBookingAvailability();
        });
        
        // Submit do agendamento
        $('#clientBookingForm').on('submit', function(e) {
            e.preventDefault();
            EspacoVIV.handleBooking();
        });
        
        // Seleção de massagista
        $(document).on('click', '.massagist-card', function() {
            $('.massagist-card').removeClass('selected');
            $(this).addClass('selected');
            EspacoVIV.selectedMassagist = $(this).data('id');
            EspacoVIV.updateTimeSlots();
        });
        
        // Seleção de horário
        $(document).on('click', '.time-slot', function() {
            $('.time-slot').removeClass('selected');
            $(this).addClass('selected');
            EspacoVIV.selectedTime = $(this).data('time');
            $('#clientBookingForm button[type="submit"]').prop('disabled', false);
        });
        
        // Máscara para telefone
        if ($.fn.mask) {
            $('#clientPhone').mask('(00) 00000-0000');
        }
    };
    
    EspacoVIV.handleLogin = function() {
        if (this.isLoading) return;
        
        var email = $('#loginEmail').val();
        var password = $('#loginPassword').val();
        
        if (!email || !password) {
            EspacoVIV.showLoginMessage('Por favor, preencha todos os campos.', 'error');
            return;
        }
        
        var $btn = $('#massagistLoginForm button[type="submit"]');
        EspacoVIV.setLoadingState($btn, true);
        
        // Simulação de login (em produção, seria uma chamada AJAX real)
        setTimeout(function() {
            if (email.includes('@') && password.length >= 6) {
                EspacoVIV.showLoginMessage('Login realizado com sucesso! Redirecionando...', 'success');
                setTimeout(function() {
                    window.location.href = 'dashboard.html';
                }, 1500);
            } else {
                EspacoVIV.showLoginMessage('E-mail ou senha inválidos.', 'error');
            }
            EspacoVIV.setLoadingState($btn, false);
        }, 1000);
    };
    
    EspacoVIV.handleRegister = function() {
        if (this.isLoading) return;
        
        var name = $('#regName').val();
        var email = $('#regEmail').val();
        var password = $('#regPassword').val();
        var unit = $('#regUnit').val();
        
        if (!name || !email || !password || !unit) {
            EspacoVIV.showLoginMessage('Por favor, preencha todos os campos obrigatórios.', 'error');
            return;
        }
        
        if (password.length < 6) {
            EspacoVIV.showLoginMessage('A senha deve ter pelo menos 6 caracteres.', 'error');
            return;
        }
        
        var $btn = $('#massagistRegisterForm button[type="submit"]');
        EspacoVIV.setLoadingState($btn, true);
        
        // Simulação de registro
        setTimeout(function() {
            EspacoVIV.showLoginMessage('Cadastro realizado com sucesso! Agora você pode fazer login.', 'success');
            setTimeout(function() {
                $('#backToLogin').click();
            }, 2000);
            EspacoVIV.setLoadingState($btn, false);
        }, 1500);
    };
    
    EspacoVIV.updateBookingAvailability = function() {
        var unit = $('#bookingUnit').val();
        var massageType = $('#bookingMassageType').val();
        var date = $('#bookingDate').val();
        
        if (unit && massageType && date) {
            EspacoVIV.loadMassagists(unit);
        }
    };
    
    EspacoVIV.loadMassagists = function(unit) {
        $('#massagistSelection').show();
        $('#massagistList').html('<div class="loading"><i class="fas fa-spinner fa-spin"></i> Carregando massagistas...</div>');
        
        // Simulação de dados (em produção seriam dados reais do backend)
        setTimeout(function() {
            var massagists = EspacoVIV.getMockMassagists(unit);
            var html = '';
            
            if (massagists.length === 0) {
                html = '<p class="no-results">Nenhuma massagista disponível para esta unidade no momento.</p>';
            } else {
                massagists.forEach(function(m) {
                    html += `
                        <div class="massagist-card" data-id="${m.id}">
                            <img src="${m.photo || '../assets/images/default-avatar.png'}" alt="${m.name}" class="massagist-photo">
                            <h4>${m.name}</h4>
                            <p class="massagist-specialties">${m.specialties}</p>
                            <span class="massagist-status online">
                                <i class="fas fa-circle"></i> Online
                            </span>
                        </div>
                    `;
                });
            }
            
            $('#massagistList').html(html);
        }, 800);
    };
    
    EspacoVIV.updateTimeSlots = function() {
        if (!EspacoVIV.selectedMassagist) return;
        
        $('#timeSelection').show();
        $('#timeSlots').html('<div class="loading"><i class="fas fa-spinner fa-spin"></i> Carregando horários...</div>');
        
        // Simulação de horários disponíveis
        setTimeout(function() {
            var times = EspacoVIV.getMockAvailableTimes();
            var html = '';
            
            times.forEach(function(time) {
                html += `<button type="button" class="time-slot" data-time="${time}">${time}</button>`;
            });
            
            $('#timeSlots').html(html);
        }, 600);
    };
    
    EspacoVIV.handleBooking = function() {
        if (this.isLoading) return;
        
        var name = $('#clientName').val();
        var phone = $('#clientPhone').val();
        var unit = $('#bookingUnit').val();
        var massageType = $('#bookingMassageType').val();
        var date = $('#bookingDate').val();
        
        if (!name || !phone || !unit || !massageType || !date || !EspacoVIV.selectedMassagist || !EspacoVIV.selectedTime) {
            EspacoVIV.showBookingMessage('Por favor, preencha todos os campos e selecione massagista e horário.', 'error');
            return;
        }
        
        var $btn = $('#clientBookingForm button[type="submit"]');
        EspacoVIV.setLoadingState($btn, true);
        
        // Simulação de agendamento
        setTimeout(function() {
            var massagistName = $('.massagist-card.selected h4').text();
            var massageTypeName = $('#bookingMassageType option:selected').text();
            var formattedDate = new Date(date).toLocaleDateString('pt-BR');
            
            $('#bookingDetails').html(`
                <p><strong>Cliente:</strong> ${name}</p>
                <p><strong>Massagista:</strong> ${massagistName}</p>
                <p><strong>Serviço:</strong> ${massageTypeName}</p>
                <p><strong>Data:</strong> ${formattedDate}</p>
                <p><strong>Horário:</strong> ${EspacoVIV.selectedTime}</p>
                <p><strong>Unidade:</strong> ${$('#bookingUnit option:selected').text()}</p>
            `);
            
            $('#clientBookingForm').hide();
            $('#bookingSuccess').show();
            
            EspacoVIV.setLoadingState($btn, false);
        }, 2000);
    };
    
    EspacoVIV.handleNewsletterSubmit = function($form) {
        var email = $form.find('input[type="email"]').val();
        
        if (!email) {
            EspacoVIV.showMessage('Por favor, digite seu e-mail.', 'error');
            return;
        }
        
        if (!EspacoVIV.isValidEmail(email)) {
            EspacoVIV.showMessage('Por favor, digite um e-mail válido.', 'error');
            return;
        }
        
        var $btn = $form.find('button[type="submit"]');
        var originalText = $btn.text();
        
        $btn.text('Cadastrando...').prop('disabled', true);
        
        // Simulação de cadastro na newsletter
        setTimeout(function() {
            EspacoVIV.showMessage('E-mail cadastrado com sucesso! Você receberá nossas promoções.', 'success');
            $form[0].reset();
            $btn.text(originalText).prop('disabled', false);
        }, 1000);
    };
    
    // Métodos utilitários
    EspacoVIV.showMessage = function(message, type) {
        // Criar e mostrar mensagem global
        var $message = $(`
            <div class="global-message ${type}">
                <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
                <span>${message}</span>
                <button class="close-message">&times;</button>
            </div>
        `);
        
        $('body').append($message);
        
        $message.fadeIn().delay(5000).fadeOut(function() {
            $(this).remove();
        });
        
        // Fechar ao clicar
        $message.find('.close-message').on('click', function() {
            $message.fadeOut(function() {
                $(this).remove();
            });
        });
    };
    
    EspacoVIV.showLoginMessage = function(message, type) {
        $('#loginMessage')
            .removeClass('success error info')
            .addClass(type)
            .html(message)
            .show();
    };
    
    EspacoVIV.showBookingMessage = function(message, type) {
        $('#bookingMessage')
            .removeClass('success error info')
            .addClass(type)
            .html(message)
            .show();
    };
    
    EspacoVIV.setLoadingState = function($btn, loading) {
        this.isLoading = loading;
        
        if (loading) {
            $btn.find('.btn-text').hide();
            $btn.find('.btn-loading').show();
            $btn.prop('disabled', true);
        } else {
            $btn.find('.btn-text').show();
            $btn.find('.btn-loading').hide();
            $btn.prop('disabled', false);
        }
    };
    
    EspacoVIV.isValidEmail = function(email) {
        var re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    };
    
    // Dados mock para demonstração
    EspacoVIV.getMockMassagists = function(unit) {
        var allMassagists = {
            'sp': [
                { id: 1, name: 'Ana Silva', specialties: 'Shiatsu, Relaxante', photo: 'assets/images/ana.jpg' },
                { id: 2, name: 'Maria Santos', specialties: 'Terapêutica, Drenagem', photo: 'assets/images/maria.jpg' },
                { id: 3, name: 'Julia Costa', specialties: 'Quick Massage, Reflexologia', photo: 'assets/images/julia.jpg' }
            ],
            'rj': [
                { id: 4, name: 'Carla Oliveira', specialties: 'Shiatsu, Terapêutica', photo: 'assets/images/carla.jpg' },
                { id: 5, name: 'Paula Lima', specialties: 'Relaxante, Drenagem', photo: 'assets/images/paula.jpg' }
            ],
            'bsb': [
                { id: 6, name: 'Lucia Ferreira', specialties: 'Quick Massage, Reflexologia', photo: 'assets/images/lucia.jpg' },
                { id: 7, name: 'Amanda Rocha', specialties: 'Shiatsu, Relaxante', photo: 'assets/images/amanda.jpg' }
            ]
        };
        
        return allMassagists[unit] || [];
    };
    
    EspacoVIV.getMockAvailableTimes = function() {
        return ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00'];
    };
    
    // Função global para scroll suave (usada pelos botões do slider)
    window.scrollToSection = function(sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.scrollIntoView({ 
                behavior: 'smooth',
                block: 'start'
            });
        }
    };

    // Expor EspacoVIV globalmente para debug
    if (window.console) {
        window.EspacoVIV = EspacoVIV;
    }
    
})(jQuery);