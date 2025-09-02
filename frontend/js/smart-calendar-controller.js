/**
 * Controlador do Calendário Inteligente do Espaço VIV
 * Gerencia todas as visualizações e funcionalidades do calendário
 */

class SmartCalendarController {
    constructor() {
        this.currentView = 'day';
        this.currentDate = new Date();
        this.currentUnit = '';
        this.currentMassagista = null;
        this.data = {
            units: [],
            services: [],
            massagistas: [],
            slots: [],
            stats: {}
        };
        
        this.init();
    }

    async init() {
        this.bindEvents();
        await this.loadInitialData();
        this.updateDisplay();
    }

    bindEvents() {
        // Seletores de visualização
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchView(e.target.dataset.view);
            });
        });

        // Navegação de data
        document.getElementById('prevDate').addEventListener('click', () => this.navigateDate(-1));
        document.getElementById('nextDate').addEventListener('click', () => this.navigateDate(1));
        document.getElementById('todayBtn').addEventListener('click', () => this.goToToday());

        // Filtros
        document.getElementById('unitSelector').addEventListener('change', (e) => {
            this.currentUnit = e.target.value;
            this.loadMassagistasByUnit();
            this.updateDisplay();
        });

        document.getElementById('massagistaFilter').addEventListener('change', (e) => {
            this.currentMassagista = e.target.value || null;
            this.updateDisplay();
        });

        // Ações
        document.getElementById('refreshCalendar').addEventListener('click', () => this.updateDisplay());
        document.getElementById('findNextSlot').addEventListener('click', () => this.findNextAvailableSlot());
        document.getElementById('toggleFilters').addEventListener('click', () => this.toggleFilters());

        // Modal events
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                this.closeModal(modal.id);
            });
        });

        // Fechar modal clicando fora
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target.id);
            }
        });
    }

    async loadInitialData() {
        try {
            this.showLoading(true);
            
            // Carregar unidades
            this.data.units = await window.apiService.getUnits();
            this.populateUnitSelector();

            // Carregar serviços
            this.data.services = await window.apiService.getServices();
            this.populateServiceFilter();

            // Se há uma unidade padrão, carregá-la
            if (this.data.units.length > 0) {
                this.currentUnit = this.data.units[0].code;
                document.getElementById('unitSelector').value = this.currentUnit;
                await this.loadMassagistasByUnit();
            }

        } catch (error) {
            console.error('Erro ao carregar dados iniciais:', error);
            this.showError('Erro ao carregar dados do calendário');
        } finally {
            this.showLoading(false);
        }
    }

    async loadMassagistasByUnit() {
        if (!this.currentUnit) return;

        try {
            this.data.massagistas = await window.apiService.getMassagistasByUnit(this.currentUnit);
            this.populateMassagistaFilter();
        } catch (error) {
            console.error('Erro ao carregar massagistas:', error);
        }
    }

    populateUnitSelector() {
        const selector = document.getElementById('unitSelector');
        selector.innerHTML = '<option value="">Todas as unidades</option>';
        
        this.data.units.forEach(unit => {
            const option = document.createElement('option');
            option.value = unit.code;
            option.textContent = unit.name;
            selector.appendChild(option);
        });
    }

    populateMassagistaFilter() {
        const selector = document.getElementById('massagistaFilter');
        selector.innerHTML = '<option value="">Todos</option>';
        
        this.data.massagistas.forEach(massagista => {
            const option = document.createElement('option');
            option.value = massagista.id;
            option.textContent = massagista.name;
            selector.appendChild(option);
        });
    }

    populateServiceFilter() {
        const selector = document.getElementById('serviceFilter');
        selector.innerHTML = '<option value="">Todos</option>';
        
        this.data.services.forEach(service => {
            const option = document.createElement('option');
            option.value = service.name;
            option.textContent = `${service.name} (${service.duration}min - R$${service.price})`;
            selector.appendChild(option);
        });
    }

    switchView(view) {
        this.currentView = view;
        
        // Atualizar botões
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });

        // Mostrar view correta
        document.querySelectorAll('.calendar-view').forEach(viewEl => {
            viewEl.classList.toggle('active', viewEl.id === `${view}View`);
        });

        this.updateDisplay();
    }

    navigateDate(direction) {
        switch (this.currentView) {
            case 'day':
                this.currentDate.setDate(this.currentDate.getDate() + direction);
                break;
            case 'week':
                this.currentDate.setDate(this.currentDate.getDate() + (direction * 7));
                break;
            case 'month':
                this.currentDate.setMonth(this.currentDate.getMonth() + direction);
                break;
        }
        
        this.updateDisplay();
    }

    goToToday() {
        this.currentDate = new Date();
        this.updateDisplay();
    }

    async updateDisplay() {
        this.updateDateTitle();
        
        switch (this.currentView) {
            case 'day':
                await this.renderDayView();
                break;
            case 'week':
                await this.renderWeekView();
                break;
            case 'month':
                await this.renderMonthView();
                break;
        }
    }

    updateDateTitle() {
        const title = document.getElementById('currentDateTitle');
        const options = { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        };

        switch (this.currentView) {
            case 'day':
                title.textContent = this.currentDate.toLocaleDateString('pt-BR', options);
                break;
            case 'week':
                const weekStart = APIUtils.getWeekStart(this.currentDate);
                const weekEnd = new Date(weekStart);
                weekEnd.setDate(weekEnd.getDate() + 6);
                title.textContent = `${weekStart.toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' })} - ${weekEnd.toLocaleDateString('pt-BR', { day: 'numeric', month: 'short', year: 'numeric' })}`;
                break;
            case 'month':
                title.textContent = this.currentDate.toLocaleDateString('pt-BR', { year: 'numeric', month: 'long' });
                break;
        }
    }

    async renderDayView() {
        if (!this.currentUnit) return;

        try {
            this.showLoading(true);
            
            const dateStr = APIUtils.formatDateForAPI(this.currentDate);
            const dayData = await window.apiService.getDayAvailability(
                this.currentUnit, 
                dateStr, 
                this.currentMassagista
            );

            this.renderTimeSlots(dayData.slots);
            this.updateStats({
                totalSlots: dayData.slots.length,
                bookedSlots: dayData.total_bookings,
                availableSlots: dayData.slots.filter(s => s.available).length,
                revenueEstimate: dayData.revenue_estimate,
                occupancyRate: dayData.slots.length > 0 ? (dayData.total_bookings / dayData.slots.length * 100) : 0
            });

            // Atualizar título do dia
            document.getElementById('dayTitle').textContent = 
                `${dayData.unit_name} - ${APIUtils.formatDateBR(this.currentDate)}`;

        } catch (error) {
            console.error('Erro ao carregar dia:', error);
            this.showError('Erro ao carregar dados do dia');
        } finally {
            this.showLoading(false);
        }
    }

    renderTimeSlots(slots) {
        const container = document.getElementById('timeSlots');
        container.innerHTML = '';

        slots.forEach(slot => {
            const slotEl = document.createElement('div');
            slotEl.className = `time-slot ${slot.available ? 'available' : 'booked'}`;
            slotEl.onclick = () => this.showSlotDetails(slot);

            slotEl.innerHTML = `
                <div class="slot-time">${slot.time}</div>
                <div class="slot-info">
                    ${slot.available ? 
                        '<div class="slot-client">Horário disponível</div>' :
                        `
                        <div class="slot-client">${slot.booked_by}</div>
                        <div class="slot-service">${slot.service}</div>
                        <div class="slot-massagista">com ${slot.massagista_name}</div>
                        `
                    }
                </div>
                <div class="slot-status ${slot.available ? 'available' : 'booked'}">
                    ${slot.available ? 'Disponível' : 'Agendado'}
                </div>
            `;

            container.appendChild(slotEl);
        });
    }

    async renderWeekView() {
        // Implementação simplificada da visão semanal
        const container = document.getElementById('weekGrid');
        container.innerHTML = '<p>Visão semanal em desenvolvimento...</p>';
        
        // Estatísticas básicas para a semana
        this.updateStats({
            totalSlots: 0,
            bookedSlots: 0,
            availableSlots: 0,
            revenueEstimate: 0,
            occupancyRate: 0
        });
    }

    async renderMonthView() {
        // Implementação simplificada da visão mensal
        const container = document.getElementById('monthGrid');
        container.innerHTML = '<p>Visão mensal em desenvolvimento...</p>';
        
        // Estatísticas básicas para o mês
        this.updateStats({
            totalSlots: 0,
            bookedSlots: 0,
            availableSlots: 0,
            revenueEstimate: 0,
            occupancyRate: 0
        });
    }

    updateStats(stats) {
        document.getElementById('totalSlots').textContent = stats.totalSlots || 0;
        document.getElementById('bookedSlots').textContent = stats.bookedSlots || 0;
        document.getElementById('availableSlots').textContent = stats.availableSlots || 0;
        document.getElementById('revenueEstimate').textContent = 
            `R$ ${(stats.revenueEstimate || 0).toFixed(2)}`;
        document.getElementById('occupancyRate').textContent = 
            `${(stats.occupancyRate || 0).toFixed(1)}%`;
    }

    async findNextAvailableSlot() {
        if (!this.currentUnit) {
            alert('Selecione uma unidade primeiro');
            return;
        }

        try {
            const dateStr = APIUtils.formatDateForAPI(this.currentDate);
            const result = await window.apiService.getNextAvailableSlot(this.currentUnit, dateStr);
            
            this.showNextSlotModal(result);
        } catch (error) {
            console.error('Erro ao buscar próximo slot:', error);
            alert('Erro ao buscar próximo horário disponível');
        }
    }

    showNextSlotModal(slotData) {
        const modal = document.getElementById('nextSlotModal');
        const resultContainer = document.getElementById('nextSlotResult');

        if (slotData.next_available) {
            const slot = slotData.next_available;
            resultContainer.innerHTML = `
                <div class="next-slot-card">
                    <h4>📅 ${APIUtils.formatDateBR(slot.date)} (${slot.day_of_week})</h4>
                    <p><strong>⏰ Horário:</strong> ${slot.time}</p>
                    <p><strong>📍 Unidade:</strong> ${this.getUnitName(this.currentUnit)}</p>
                    <p><strong>🗓️ Em:</strong> ${slot.days_from_now === 0 ? 'Hoje' : `${slot.days_from_now} dias`}</p>
                </div>

                <div class="alternatives">
                    <h5>Outros horários disponíveis no mesmo dia:</h5>
                    <div class="alternative-times">
                        ${slotData.alternatives.map(alt => 
                            `<span class="time-badge ${alt.available ? 'available' : 'unavailable'}">
                                ${alt.time}
                            </span>`
                        ).join('')}
                    </div>
                </div>
            `;

            // Configurar botão de agendamento
            document.getElementById('bookNextSlot').onclick = () => {
                this.bookSlot(slot.date, slot.time);
            };
        } else {
            resultContainer.innerHTML = `
                <div class="no-slots">
                    <p>😔 Nenhum horário disponível encontrado nos próximos 30 dias.</p>
                    <p>Tente uma unidade diferente ou entre em contato conosco.</p>
                </div>
            `;
            document.getElementById('bookNextSlot').style.display = 'none';
        }

        modal.style.display = 'block';
    }

    showSlotDetails(slot) {
        const modal = document.getElementById('slotDetailsModal');
        const titleEl = document.getElementById('slotModalTitle');
        const detailsEl = document.getElementById('slotDetails');
        const bookBtn = document.getElementById('bookSlot');
        const cancelBtn = document.getElementById('cancelBooking');

        if (slot.available) {
            titleEl.textContent = 'Agendar Horário';
            detailsEl.innerHTML = `
                <div class="slot-detail-card">
                    <h4>⏰ ${slot.time}</h4>
                    <p><strong>📅 Data:</strong> ${APIUtils.formatDateBR(this.currentDate)}</p>
                    <p><strong>📍 Unidade:</strong> ${this.getUnitName(this.currentUnit)}</p>
                    <p><strong>✅ Status:</strong> Disponível para agendamento</p>
                </div>
            `;
            bookBtn.style.display = 'inline-block';
            cancelBtn.style.display = 'none';
            
            bookBtn.onclick = () => {
                const dateStr = APIUtils.formatDateForAPI(this.currentDate);
                this.bookSlot(dateStr, slot.time);
            };
        } else {
            titleEl.textContent = 'Detalhes do Agendamento';
            detailsEl.innerHTML = `
                <div class="slot-detail-card">
                    <h4>⏰ ${slot.time}</h4>
                    <p><strong>👤 Cliente:</strong> ${slot.booked_by}</p>
                    <p><strong>💆 Serviço:</strong> ${slot.service}</p>
                    <p><strong>👩‍⚕️ Massagista:</strong> ${slot.massagista_name}</p>
                    <p><strong>📅 Data:</strong> ${APIUtils.formatDateBR(this.currentDate)}</p>
                    <p><strong>📍 Unidade:</strong> ${this.getUnitName(this.currentUnit)}</p>
                </div>
            `;
            bookBtn.style.display = 'none';
            cancelBtn.style.display = 'inline-block';
        }

        modal.style.display = 'block';
    }

    bookSlot(date, time) {
        // Aqui você pode integrar com um modal de agendamento
        // ou redirecionar para a página de agendamento
        alert(`Funcionalidade de agendamento será implementada.\nData: ${date}\nHorário: ${time}`);
        this.closeModal('slotDetailsModal');
        this.closeModal('nextSlotModal');
    }

    getUnitName(unitCode) {
        const unit = this.data.units.find(u => u.code === unitCode);
        return unit ? unit.name : unitCode;
    }

    toggleFilters() {
        const filters = document.getElementById('calendarFilters');
        const btn = document.getElementById('toggleFilters');
        
        if (filters.style.display === 'none') {
            filters.style.display = 'flex';
            btn.textContent = '🔼 Filtros';
        } else {
            filters.style.display = 'none';
            btn.textContent = '🔽 Filtros';
        }
    }

    showLoading(show) {
        const loading = document.getElementById('calendarLoading');
        loading.style.display = show ? 'block' : 'none';
    }

    showError(message) {
        console.error(message);
        // Você pode implementar um sistema de notificação aqui
        alert(message);
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.style.display = 'none';
    }
}

// ============================================================================
// FUNÇÕES GLOBAIS
// ============================================================================

function closeModal(modalId) {
    if (window.smartCalendar) {
        window.smartCalendar.closeModal(modalId);
    }
}

// ============================================================================
// INICIALIZAÇÃO
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Aguardar API Service estar carregado
    if (window.apiService) {
        window.smartCalendar = new SmartCalendarController();
        console.log('📅 Smart Calendar Controller carregado!');
    } else {
        setTimeout(() => {
            window.smartCalendar = new SmartCalendarController();
            console.log('📅 Smart Calendar Controller carregado!');
        }, 200);
    }
});

// Exportar para uso global
window.SmartCalendarController = SmartCalendarController;