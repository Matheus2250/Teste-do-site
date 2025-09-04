class BookingModal {
    constructor() {
        this.selectedUnit = '';
        this.selectedMassagista = '';
        this.selectedService = '';
        this.selectedDate = '';
        this.selectedTime = '';
        this.currentStep = 1;
        this.currentMassagistas = [];
        
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
    
    async loadMassagistasByUnit() {
        this.selectedUnit = document.getElementById('unitSelect').value;
        if (!this.selectedUnit) return;
        
        const grid = document.getElementById('massagistaGrid');
        
        try {
            // Call API to get massagistas by unit
            const response = await fetch(`http://localhost:10000/api/massagista/by-unit/${this.selectedUnit}`);
            
            if (response.ok) {
                const unitMassagistas = await response.json();
                
                if (unitMassagistas.length === 0) {
                    grid.innerHTML = '<p>Nenhuma massagista disponível nesta unidade no momento.</p>';
                    return;
                }
                
                grid.innerHTML = unitMassagistas.map((massagista, index) => `
                    <div class="massagista-card" onclick="bookingModal.selectMassagista(${massagista.id}, '${massagista.name}')">
                        <div class="avatar-placeholder">${massagista.name.charAt(0)}</div>
                        <h4>${massagista.name}</h4>
                        <p>${massagista.specialties.join(', ')}</p>
                        <span class="status ${massagista.is_available ? 'online' : 'offline'}">
                            ${massagista.is_available ? 'Disponível' : 'Ocupada'}
                        </span>
                    </div>
                `).join('');
                
                // Store massagistas data for selection
                this.currentMassagistas = unitMassagistas;
                
            } else {
                console.error('Erro na resposta da API:', response.status);
                grid.innerHTML = '<p>Erro ao carregar massagistas. Tente novamente.</p>';
            }
        } catch (error) {
            console.error('Erro ao carregar massagistas da unidade:', error);
            grid.innerHTML = '<p>Erro ao carregar massagistas. Tente novamente.</p>';
        }
        
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
async function loadMassagistasByUnit() {
    await bookingModal.loadMassagistasByUnit();
}

function openAgendamento(promocao) {
    bookingModal.openModal(promocao);
}