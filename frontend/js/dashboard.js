/**
 * Espaço VIV - Dashboard Massagista
 * JavaScript para o painel de controle das massagistas
 */

(function($) {
    'use strict';
    
    // Variáveis globais
    var Dashboard = {
        isLoading: false,
        currentUser: null,
        currentTab: 'agenda'
    };
    
    // Inicializar quando documento estiver pronto
    $(document).ready(function() {
        Dashboard.init();
    });
    
    Dashboard.init = function() {
        // Verificar se usuário está logado
        this.checkAuth();
        
        // Inicializar componentes
        this.initTabs();
        this.initForms();
        this.initDateInputs();
        
        // Carregar dados iniciais
        this.loadUserData();
        this.loadStats();
        this.loadAgenda();
        
        // Bind de eventos
        this.bindEvents();
        
        console.log('Dashboard initialized');
    };
    
    Dashboard.checkAuth = function() {
        // Em produção, verificaria se o usuário está autenticado
        // Por ora, simulamos dados de usuário
        this.currentUser = {
            id: 1,
            name: 'Ana Silva',
            email: 'ana@espacoviv.com',
            unit: 'sp',
            phone: '(11) 99999-9999',
            photo_url: 'assets/images/ana.jpg',
            massage_types: 'Shiatsu, Relaxante, Terapêutica',
            is_online: true
        };
    };
    
    Dashboard.initTabs = function() {
        // Navegação entre abas
        $('.tab-btn').on('click', function() {
            var tabId = $(this).data('tab');
            Dashboard.switchTab(tabId);
        });
    };
    
    Dashboard.initForms = function() {
        // Máscaras
        if ($.fn.mask) {
            $('#profilePhone').mask('(00) 00000-0000');
        }
        
        // Formulários
        $('#profileForm').on('submit', function(e) {
            e.preventDefault();
            Dashboard.updateProfile();
        });
        
        $('#scheduleForm').on('submit', function(e) {
            e.preventDefault();
            Dashboard.updateSchedule();
        });
    };
    
    Dashboard.initDateInputs = function() {
        // Data de hoje para agenda
        var today = new Date().toISOString().split('T')[0];
        $('#agendaDate').val(today);
        
        // Checkbox de dias da semana
        $('.day-checkbox input').on('change', function() {
            var $dayTimes = $(this).closest('.schedule-day').find('.day-times');
            if ($(this).is(':checked')) {
                $dayTimes.show();
            } else {
                $dayTimes.hide();
            }
        });
    };
    
    Dashboard.bindEvents = function() {
        // Toggle status online/offline
        $('#statusToggle').on('change', function() {
            Dashboard.toggleStatus();
        });
        
        // Botões de ação
        $('#refreshBtn').on('click', function() {
            Dashboard.refreshData();
        });
        
        $('#logoutBtn').on('click', function() {
            Dashboard.logout();
        });
        
        // Carregar agenda por data
        $('#loadAgenda').on('click', function() {
            Dashboard.loadAgenda();
        });
        
        // Carregar histórico
        $('#loadHistory').on('click', function() {
            Dashboard.loadHistory();
        });
    };
    
    Dashboard.loadUserData = function() {
        if (!this.currentUser) return;
        
        // Atualizar interface com dados do usuário
        $('#userName').text(this.currentUser.name);
        $('#userUnit').text(this.getUnitName(this.currentUser.unit));
        $('#userPhoto').attr('src', this.currentUser.photo_url || 'assets/images/default-avatar.png');
        
        // Status online/offline
        $('#statusToggle').prop('checked', this.currentUser.is_online);
        $('#statusText').text(this.currentUser.is_online ? 'Online' : 'Offline');
        
        // Formulário de perfil
        $('#profileName').val(this.currentUser.name);
        $('#profileEmail').val(this.currentUser.email);
        $('#profilePhone').val(this.currentUser.phone || '');
        $('#profilePhoto').val(this.currentUser.photo_url || '');
        $('#profileMassageTypes').val(this.currentUser.massage_types || '');
        
        // Unidade (select)
        var unitSelect = `
            <option value="sp" ${this.currentUser.unit === 'sp' ? 'selected' : ''}>São Paulo - Perdizes</option>
            <option value="rj" ${this.currentUser.unit === 'rj' ? 'selected' : ''}>Rio de Janeiro - Centro</option>
            <option value="bsb" ${this.currentUser.unit === 'bsb' ? 'selected' : ''}>Brasília - SHS</option>
        `;
        $('#profileUnit').html(unitSelect);
    };
    
    Dashboard.loadStats = function() {
        // Simular carregamento de estatísticas
        $('#loadingOverlay').show();
        
        setTimeout(function() {
            // Dados simulados
            $('#todayCount').text('3');
            $('#weekCount').text('18');
            $('#completedCount').text('145');
            $('#pendingCount').text('2');
            
            $('#loadingOverlay').hide();
        }, 800);
    };
    
    Dashboard.loadAgenda = function() {
        var date = $('#agendaDate').val() || new Date().toISOString().split('T')[0];
        
        $('#agendaContent').html('<div class="loading-content"><i class="fas fa-spinner fa-spin"></i> Carregando agenda...</div>');
        
        // Simular carregamento da agenda
        setTimeout(function() {
            var appointments = Dashboard.getMockAppointments(date);
            Dashboard.displayAgenda(appointments, date);
        }, 1000);
    };
    
    Dashboard.loadHistory = function() {
        var period = $('#historyPeriod').val();
        
        $('#historyContent').html('<div class="loading-content"><i class="fas fa-spinner fa-spin"></i> Carregando histórico...</div>');
        
        // Simular carregamento do histórico
        setTimeout(function() {
            var history = Dashboard.getMockHistory(period);
            Dashboard.displayHistory(history);
        }, 1000);
    };
    
    Dashboard.switchTab = function(tabId) {
        // Atualizar botões
        $('.tab-btn').removeClass('active');
        $(`[data-tab="${tabId}"]`).addClass('active');
        
        // Atualizar conteúdo
        $('.tab-content').removeClass('active');
        $(`#tab-${tabId}`).addClass('active');
        
        this.currentTab = tabId;
        
        // Carregar dados específicos da aba
        if (tabId === 'agenda') {
            this.loadAgenda();
        } else if (tabId === 'historico') {
            this.loadHistory();
        }
    };
    
    Dashboard.toggleStatus = function() {
        if (this.isLoading) return;
        
        var isOnline = $('#statusToggle').is(':checked');
        this.isLoading = true;
        
        // Simular chamada para backend
        setTimeout(function() {
            Dashboard.currentUser.is_online = isOnline;
            $('#statusText').text(isOnline ? 'Online' : 'Offline');
            
            Dashboard.showMessage(
                isOnline ? 'Você está agora online e visível para clientes.' : 'Você está agora offline.',
                'success'
            );
            
            Dashboard.isLoading = false;
        }, 500);
    };
    
    Dashboard.updateProfile = function() {
        if (this.isLoading) return;
        
        var $btn = $('#profileForm').find('button[type="submit"]');
        this.setLoadingState($btn, true);
        
        // Coletar dados do formulário
        var data = {
            name: $('#profileName').val(),
            phone: $('#profilePhone').val(),
            photo_url: $('#profilePhoto').val(),
            massage_types: $('#profileMassageTypes').val()
        };
        
        // Simular atualização
        setTimeout(function() {
            // Atualizar dados locais
            Dashboard.currentUser.name = data.name;
            Dashboard.currentUser.phone = data.phone;
            Dashboard.currentUser.photo_url = data.photo_url;
            Dashboard.currentUser.massage_types = data.massage_types;
            
            // Atualizar interface
            $('#userName').text(data.name);
            if (data.photo_url) {
                $('#userPhoto').attr('src', data.photo_url);
            }
            
            Dashboard.showMessage('Perfil atualizado com sucesso!', 'success');
            Dashboard.setLoadingState($btn, false);
        }, 1500);
    };
    
    Dashboard.updateSchedule = function() {
        if (this.isLoading) return;
        
        var $btn = $('#scheduleForm').find('button[type="submit"]');
        this.setLoadingState($btn, true);
        
        // Coletar horários selecionados
        var schedule = {};
        $('.schedule-day').each(function() {
            var $day = $(this);
            var dayCheckbox = $day.find('.day-checkbox input');
            
            if (dayCheckbox.is(':checked')) {
                var day = dayCheckbox.data('day');
                var startTime = $day.find('input[name*="[start]"]').val();
                var endTime = $day.find('input[name*="[end]"]').val();
                
                schedule[day] = {
                    start: startTime,
                    end: endTime
                };
            }
        });
        
        // Simular salvamento
        setTimeout(function() {
            Dashboard.showMessage('Horários de trabalho atualizados com sucesso!', 'success');
            Dashboard.setLoadingState($btn, false);
        }, 1000);
    };
    
    Dashboard.refreshData = function() {
        this.showMessage('Atualizando dados...', 'info');
        this.loadStats();
        this.loadAgenda();
    };
    
    Dashboard.logout = function() {
        if (confirm('Tem certeza que deseja sair?')) {
            this.showMessage('Saindo...', 'info');
            setTimeout(function() {
                window.location.href = 'index.html';
            }, 1000);
        }
    };
    
    Dashboard.displayAgenda = function(appointments, date) {
        var formattedDate = new Date(date).toLocaleDateString('pt-BR');
        var html = `<h3>Agendamentos para ${formattedDate}</h3>`;
        
        if (appointments.length === 0) {
            html += '<div class="empty-state"><i class="fas fa-calendar-times"></i><p>Nenhum agendamento para esta data.</p></div>';
        } else {
            html += '<div class="appointments-list">';
            
            appointments.forEach(function(appointment) {
                html += `
                    <div class="appointment-card ${appointment.status}">
                        <div class="appointment-time">
                            <strong>${appointment.time}</strong>
                            <small>${appointment.duration} min</small>
                        </div>
                        <div class="appointment-info">
                            <h4>${appointment.client_name}</h4>
                            <p class="service">${appointment.service}</p>
                            ${appointment.client_phone ? `<p class="phone"><i class="fas fa-phone"></i> ${appointment.client_phone}</p>` : ''}
                            ${appointment.notes ? `<p class="notes"><i class="fas fa-comment"></i> ${appointment.notes}</p>` : ''}
                        </div>
                        <div class="appointment-actions">
                            <span class="status-badge ${appointment.status}">
                                ${Dashboard.getStatusName(appointment.status)}
                            </span>
                            ${appointment.status === 'pending' ? `
                                <div class="action-buttons">
                                    <button onclick="Dashboard.updateAppointmentStatus(${appointment.id}, 'confirmed')" class="btn-mini btn-success">
                                        <i class="fas fa-check"></i>
                                    </button>
                                    <button onclick="Dashboard.updateAppointmentStatus(${appointment.id}, 'cancelled')" class="btn-mini btn-danger">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
        }
        
        $('#agendaContent').html(html);
    };
    
    Dashboard.displayHistory = function(history) {
        var html = '<div class="history-list">';
        
        if (history.length === 0) {
            html += '<div class="empty-state"><i class="fas fa-history"></i><p>Nenhum histórico encontrado para o período selecionado.</p></div>';
        } else {
            history.forEach(function(item) {
                html += `
                    <div class="history-item">
                        <div class="history-date">${item.date}</div>
                        <div class="history-info">
                            <strong>${item.client_name}</strong> - ${item.service}
                            <div class="history-details">
                                ${item.time} • ${item.duration} min
                                ${item.rating ? ` • <i class="fas fa-star"></i> ${item.rating}/5` : ''}
                            </div>
                        </div>
                        <div class="history-status">
                            <span class="status-badge ${item.status}">
                                ${Dashboard.getStatusName(item.status)}
                            </span>
                        </div>
                    </div>
                `;
            });
        }
        
        html += '</div>';
        $('#historyContent').html(html);
    };
    
    Dashboard.updateAppointmentStatus = function(appointmentId, status) {
        if (confirm(`Confirma a ${status === 'confirmed' ? 'confirmação' : 'cancelamento'} deste agendamento?`)) {
            this.showMessage(
                status === 'confirmed' ? 'Agendamento confirmado!' : 'Agendamento cancelado!',
                'success'
            );
            // Recarregar agenda após um breve delay
            setTimeout(function() {
                Dashboard.loadAgenda();
            }, 1000);
        }
    };
    
    // Métodos utilitários
    Dashboard.showMessage = function(message, type) {
        $('#messageContainer').html(`
            <div class="message-toast ${type}">
                <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
                <span>${message}</span>
            </div>
        `).show();
        
        setTimeout(function() {
            $('#messageContainer').fadeOut();
        }, 4000);
    };
    
    Dashboard.setLoadingState = function($btn, loading) {
        this.isLoading = loading;
        
        if (loading) {
            $btn.prop('disabled', true);
            $btn.html('<i class="fas fa-spinner fa-spin"></i> Salvando...');
        } else {
            $btn.prop('disabled', false);
            $btn.html('<i class="fas fa-save"></i> Salvar Alterações');
        }
    };
    
    Dashboard.getUnitName = function(unit) {
        var units = {
            'sp': 'São Paulo - Perdizes',
            'rj': 'Rio de Janeiro - Centro',
            'bsb': 'Brasília - SHS'
        };
        return units[unit] || 'Unidade não definida';
    };
    
    Dashboard.getStatusName = function(status) {
        var statuses = {
            'pending': 'Pendente',
            'confirmed': 'Confirmado',
            'completed': 'Concluído',
            'cancelled': 'Cancelado'
        };
        return statuses[status] || status;
    };
    
    // Dados mock para demonstração
    Dashboard.getMockAppointments = function(date) {
        // Retornar diferentes dados baseados na data
        if (date === new Date().toISOString().split('T')[0]) { // Hoje
            return [
                {
                    id: 1,
                    time: '09:00',
                    duration: 60,
                    client_name: 'Maria Silva',
                    service: 'Shiatsu',
                    client_phone: '(11) 99999-1234',
                    notes: 'Primeira vez, problema nas costas',
                    status: 'confirmed'
                },
                {
                    id: 2,
                    time: '14:30',
                    duration: 15,
                    client_name: 'João Santos',
                    service: 'Quick Massage',
                    client_phone: '(11) 88888-5678',
                    notes: '',
                    status: 'pending'
                },
                {
                    id: 3,
                    time: '16:00',
                    duration: 75,
                    client_name: 'Ana Costa',
                    service: 'Massagem Terapêutica',
                    client_phone: '(11) 77777-9012',
                    notes: 'Tensão no pescoço',
                    status: 'confirmed'
                }
            ];
        } else {
            return [];
        }
    };
    
    Dashboard.getMockHistory = function(period) {
        return [
            {
                id: 1,
                date: '28/08/2024',
                time: '10:00',
                duration: 60,
                client_name: 'Carlos Mendes',
                service: 'Relaxante',
                status: 'completed',
                rating: 5
            },
            {
                id: 2,
                date: '27/08/2024',
                time: '15:30',
                duration: 45,
                client_name: 'Lucia Ferreira',
                service: 'Reflexologia',
                status: 'completed',
                rating: 4
            },
            {
                id: 3,
                date: '26/08/2024',
                time: '11:00',
                duration: 60,
                client_name: 'Pedro Oliveira',
                service: 'Shiatsu',
                status: 'cancelled',
                rating: null
            }
        ];
    };
    
    // Expor Dashboard globalmente
    window.Dashboard = Dashboard;
    
})(jQuery);