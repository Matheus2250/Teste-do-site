class BookingModal {
    constructor() {
        this.selectedUnit = '';
        this.selectedMassagista = '';
        this.selectedService = '';
        this.selectedDate = '';
        this.selectedTime = '';
        this.currentStep = 1;
        this.massagistas = {
            'sp-perdizes': [
                { id: 1, name: 'Ana Silva', specialties: 'Shiatsu, Relaxante', avatar: '../assets/images/default-avatar.png' },
                { id: 2, name: 'Maria Santos', specialties: 'Quick, Terapêutica', avatar: '../assets/images/default-avatar.png' },
                { id: 3, name: 'Julia Costa', specialties: 'Drenagem, Relaxante', avatar: '../assets/images/default-avatar.png' }
            ],
            'sp-vila-clementino': [
                { id: 4, name: 'Patricia Lima', specialties: 'Shiatsu, Pedras Quentes', avatar: '../assets/images/default-avatar.png' },
                { id: 5, name: 'Fernanda Alves', specialties: 'Quick, Relaxante', avatar: '../assets/images/default-avatar.png' }
            ],
            'sp-ingleses': [
                { id: 6, name: 'Carla Rodrigues', specialties: 'Terapêutica, Shiatsu', avatar: '../assets/images/default-avatar.png' },
                { id: 7, name: 'Roberta Nascimento', specialties: 'Relaxante, Drenagem', avatar: '../assets/images/default-avatar.png' },
                { id: 8, name: 'Camila Ferreira', specialties: 'Quick, Pedras Quentes', avatar: '../assets/images/default-avatar.png' }
            ],
            'sp-prudente': [
                { id: 9, name: 'Luciana Oliveira', specialties: 'Shiatsu, Relaxante', avatar: '../assets/images/default-avatar.png' }
            ],
            'rj-centro': [
                { id: 10, name: 'Renata Castro', specialties: 'Quick, Terapêutica', avatar: '../assets/images/default-avatar.png' },
                { id: 11, name: 'Beatriz Moreira', specialties: 'Relaxante, Drenagem', avatar: '../assets/images/default-avatar.png' }
            ],
            'rj-copacabana': [
                { id: 12, name: 'Vanessa Silva', specialties: 'Shiatsu, Pedras Quentes', avatar: '../assets/images/default-avatar.png' },
                { id: 13, name: 'Claudia Santos', specialties: 'Quick, Relaxante', avatar: '../assets/images/default-avatar.png' },
                { id: 14, name: 'Adriana Lima', specialties: 'Terapêutica, Drenagem', avatar: '../assets/images/default-avatar.png' }
            ],
            'bsb-sudoeste': [
                { id: 15, name: 'Monica Pereira', specialties: 'Shiatsu, Relaxante', avatar: '../assets/images/default-avatar.png' },
                { id: 16, name: 'Daniela Costa', specialties: 'Quick, Terapêutica', avatar: '../assets/images/default-avatar.png' }
            ],
            'bsb-asa-sul': [
                { id: 17, name: 'Sandra Oliveira', specialties: 'Relaxante, Drenagem', avatar: '../assets/images/default-avatar.png' },
                { id: 18, name: 'Helena Rodrigues', specialties: 'Shiatsu, Pedras Quentes', avatar: '../assets/images/default-avatar.png' }
            ]
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
    }
    
    bindEvents() {
        // Modal close events
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-close')) {
                this.closeModal();
            }
            if (e.target.classList.contains('modal')) {
                this.closeModal();
            }
        });
        
        // Service selection
        const serviceSelect = document.getElementById('serviceSelect');
        if (serviceSelect) {
            serviceSelect.addEventListener('change', () => {
                this.selectedService = serviceSelect.value;
                if (this.selectedService) {
                    setTimeout(() => this.showStep(4), 500);
                    this.generateSmartCalendar();
                }
            });
        }
    }
    
    openModal(promocao = null) {
        const modal = document.getElementById('agendamentoModal');
        if (promocao) {
            const promocaoInfo = document.getElementById('promocaoInfo');
            if (promocaoInfo) {
                promocaoInfo.textContent = 'Promoção selecionada: ' + promocao;
            }
        }
        modal.style.display = 'block';
        this.showStep(1);
    }
    
    closeModal() {
        const modal = document.getElementById('agendamentoModal');
        modal.style.display = 'none';
        this.resetForm();
    }
    
    resetForm() {
        this.selectedUnit = '';
        this.selectedMassagista = '';
        this.selectedService = '';
        this.selectedDate = '';
        this.selectedTime = '';
        this.currentStep = 1;
    }
    
    loadMassagistasByUnit() {
        this.selectedUnit = document.getElementById('unitSelect').value;
        if (!this.selectedUnit) return;
        
        const unitMassagistas = this.massagistas[this.selectedUnit] || [];
        const grid = document.getElementById('massagistaGrid');
        
        grid.innerHTML = unitMassagistas.map(m => `
            <div class="massagista-card" onclick="bookingModal.selectMassagista(${m.id}, '${m.name}')">
                <img src="${m.avatar}" alt="${m.name}">
                <h4>${m.name}</h4>
                <p>${m.specialties}</p>
            </div>
        `).join('');
        
        this.showStep(2);
    }
    
    selectMassagista(id, name) {
        this.selectedMassagista = { id, name };
        
        document.querySelectorAll('.massagista-card').forEach(card => card.classList.remove('selected'));
        event.currentTarget.classList.add('selected');
        
        setTimeout(() => this.showStep(3), 500);
    }
    
    generateSmartCalendar() {
        const calendar = document.getElementById('smartCalendar');
        const today = new Date();
        const nextWeek = new Date(today.getTime() + (7 * 24 * 60 * 60 * 1000));
        
        calendar.innerHTML = `
            <div class="calendar-section">
                <h4 style="margin-bottom: 10px; color: #47103C;">Selecione uma Data</h4>
                <div class="calendar-dates">
                    ${this.generateCalendarDates(today, nextWeek)}
                </div>
            </div>
            <div class="calendar-section">
                <h4 style="margin-bottom: 10px; color: #47103C;">Horários Disponíveis</h4>
                <div id="timeSlots" class="time-slots">
                    <div class="time-slot unavailable">Selecione uma data</div>
                </div>
            </div>
        `;
    }
    
    generateCalendarDates(startDate, endDate) {
        const dates = [];
        const current = new Date(startDate);
        
        while (current <= endDate) {
            const dayOfWeek = current.getDay();
            const isAvailable = dayOfWeek !== 0;
            const dateStr = current.toISOString().split('T')[0];
            
            dates.push(`
                <div class="calendar-day ${isAvailable ? 'available' : 'unavailable'}" 
                     onclick="${isAvailable ? `bookingModal.selectDate('${dateStr}')` : ''}"
                     data-date="${dateStr}">
                    ${current.getDate()}
                </div>
            `);
            
            current.setDate(current.getDate() + 1);
        }
        
        return dates.join('');
    }
    
    selectDate(dateStr) {
        this.selectedDate = dateStr;
        
        document.querySelectorAll('.calendar-day').forEach(day => day.classList.remove('selected'));
        document.querySelector(`[data-date="${dateStr}"]`).classList.add('selected');
        
        this.generateTimeSlots();
    }
    
    generateTimeSlots() {
        const timeSlots = document.getElementById('timeSlots');
        const availableTimes = ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00'];
        
        timeSlots.innerHTML = availableTimes.map(time => `
            <div class="time-slot available" onclick="bookingModal.selectTime('${time}')">
                ${time}
            </div>
        `).join('');
    }
    
    selectTime(time) {
        this.selectedTime = time;
        
        document.querySelectorAll('.time-slot').forEach(slot => slot.classList.remove('selected'));
        event.currentTarget.classList.add('selected');
        
        setTimeout(() => this.showStep(5), 500);
        this.generateBookingSummary();
    }
    
    generateBookingSummary() {
        const unitName = document.getElementById('unitSelect').selectedOptions[0].text;
        const serviceName = document.getElementById('serviceSelect').selectedOptions[0].text;
        const date = new Date(this.selectedDate).toLocaleDateString('pt-BR');
        
        const summary = document.getElementById('bookingSummary');
        summary.innerHTML = `
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                <p><strong>Unidade:</strong> ${unitName}</p>
                <p><strong>Massagista:</strong> ${this.selectedMassagista.name}</p>
                <p><strong>Serviço:</strong> ${serviceName}</p>
                <p><strong>Data:</strong> ${date}</p>
                <p><strong>Horário:</strong> ${this.selectedTime}</p>
            </div>
        `;
    }
    
    showStep(stepNum) {
        for (let i = 1; i <= 5; i++) {
            const step = document.getElementById(`step${i}`);
            if (step) {
                step.style.display = 'none';
                step.classList.remove('active');
            }
        }
        
        const currentStep = document.getElementById(`step${stepNum}`);
        if (currentStep) {
            currentStep.style.display = 'block';
            currentStep.classList.add('active');
        }
        
        this.updateProgress(stepNum);
        this.currentStep = stepNum;
    }
    
    updateProgress(stepNum) {
        const steps = document.querySelectorAll('.progress-step');
        steps.forEach((step, index) => {
            step.classList.remove('active', 'completed');
            if (index + 1 < stepNum) {
                step.classList.add('completed');
            } else if (index + 1 === stepNum) {
                step.classList.add('active');
            }
        });
    }
    
    async submitBooking(formData) {
        try {
            const bookingData = {
                client_name: formData.get('clientName'),
                phone: formData.get('phone'),
                unit_id: this.selectedUnit,
                massagista_id: this.selectedMassagista.id,
                service: this.selectedService,
                appointment_date: this.selectedDate,
                appointment_time: this.selectedTime,
                notes: formData.get('notes'),
                promotion: document.getElementById('promocaoInfo')?.textContent || null
            };
            
            const response = await fetch('/api/bookings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(bookingData)
            });
            
            if (response.ok) {
                alert('Agendamento solicitado com sucesso! Entraremos em contato em breve.');
                this.closeModal();
                return true;
            } else {
                throw new Error('Erro ao enviar agendamento');
            }
        } catch (error) {
            alert('Erro ao enviar agendamento. Tente novamente.');
            return false;
        }
    }
}

// Global instance
const bookingModal = new BookingModal();

// Global functions for backward compatibility
function loadMassagistasByUnit() {
    bookingModal.loadMassagistasByUnit();
}

function openAgendamento(promocao) {
    bookingModal.openModal(promocao);
}