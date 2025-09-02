# 🌿 Espaço VIV - APIs Desenvolvidas

## 📋 Resumo das APIs Criadas

### 🔐 Autenticação (`/api/auth/`)

#### 1. **Registro de Usuário** - `POST /auth/register`
- ✅ Validação completa de CPF brasileiro
- ✅ Validação de força da senha (maiúscula, minúscula, número, especial)
- ✅ Validação de formato de telefone
- ✅ Validação de idade (18-80 anos)
- ✅ Campos adicionais: data nascimento, gênero, anos de experiência

**Exemplo de Request:**
```json
{
  "name": "Ana Silva",
  "email": "ana@espacoviv.com",
  "password": "MinhaSenh@123",
  "cpf": "123.456.789-00",
  "phone": "(11) 99999-9999",
  "unit_preference": "sp-perdizes",
  "specialties": ["Shiatsu", "Relaxante"],
  "birth_date": "1990-05-15",
  "gender": "F",
  "experience_years": 5
}
```

#### 2. **Login** - `POST /auth/login`
- ✅ Autenticação com JWT
- ✅ Verificação de usuário ativo
- ✅ Token válido por 24 horas

#### 3. **Esqueci a Senha** - `POST /auth/forgot-password`
- ✅ Geração de código de 6 dígitos
- ✅ Envio por email (HTML formatado)
- ✅ Código válido por 1 hora
- ✅ Logs para desenvolvimento quando email não configurado

#### 4. **Redefinir Senha** - `POST /auth/reset-password`
- ✅ Validação de token
- ✅ Verificação de expiração
- ✅ Limpeza automática do token após uso

#### 5. **Alterar Senha** - `POST /auth/change-password`
- ✅ Verificação da senha atual
- ✅ Validação de força da nova senha
- ✅ Impede reutilização da senha atual

#### 6. **Atualizar Perfil** - `PUT /auth/profile`
- ✅ Atualização de dados pessoais
- ✅ Atualização de especialidades
- ✅ Validação de campos

#### 7. **Validar Senha** - `POST /auth/validate-password`
- ✅ Feedback em tempo real sobre força da senha
- ✅ Lista de critérios não atendidos
- ✅ Score de 0 a 5

#### 8. **Perfil Completo** - `GET /auth/profile/complete`
- ✅ Dados completos do usuário e massagista
- ✅ Inclui especialidades e preferências

#### 9. **Usuário Atual** - `GET /auth/me`
- ✅ Informações básicas do usuário logado

#### 10. **Logout** - `POST /auth/logout`
- ✅ Confirmação de logout

---

### 📅 Calendário Inteligente (`/api/calendar/`)

#### 1. **Disponibilidade do Dia** - `GET /calendar/availability/day/{unit_code}/{date}`
- ✅ Slots disponíveis e ocupados
- ✅ Detalhes de cada agendamento
- ✅ Estimativa de receita
- ✅ Informações do massagista por slot

**Exemplo de Response:**
```json
{
  "date": "2024-09-03",
  "unit_name": "São Paulo - Perdizes",
  "slots": [
    {
      "time": "09:00",
      "available": true,
      "booked_by": null,
      "service": null,
      "massagista_name": null
    },
    {
      "time": "10:00",
      "available": false,
      "booked_by": "Maria Santos",
      "service": "Shiatsu",
      "massagista_name": "Ana Silva"
    }
  ],
  "total_bookings": 3,
  "revenue_estimate": 300.0
}
```

#### 2. **Disponibilidade da Semana** - `GET /calendar/availability/week/{unit_code}`
- ✅ Visão completa de 7 dias
- ✅ Estatísticas da semana
- ✅ Identificação de fins de semana e feriados
- ✅ Taxa de ocupação

#### 3. **Disponibilidade do Mês** - `GET /calendar/availability/month/{unit_code}/{year}/{month}`
- ✅ Visão completa do mês
- ✅ Organização por semanas
- ✅ Estatísticas mensais
- ✅ Identificação da semana mais movimentada

#### 4. **Estatísticas Avançadas** - `GET /calendar/stats/availability`
- ✅ Análise de padrões por horário
- ✅ Serviços mais populares
- ✅ Taxa de ocupação
- ✅ Estimativas de receita
- ✅ Filtros por unidade e massagista

**Exemplo de Response:**
```json
{
  "period": {
    "from": "2024-08-01",
    "to": "2024-09-01",
    "days": 32
  },
  "bookings": {
    "total": 156,
    "average_per_day": 4.9,
    "occupancy_rate": 65.2
  },
  "patterns": {
    "peak_hour": "15:00",
    "popular_service": "Shiatsu",
    "hourly_distribution": {
      "09:00": 12,
      "10:00": 18,
      "15:00": 25
    }
  },
  "revenue": {
    "estimated_total": 15600.0,
    "average_per_booking": 100.0,
    "average_per_day": 487.5
  }
}
```

#### 5. **Próximo Slot Disponível** - `GET /calendar/next-available/{unit_code}`
- ✅ Busca nos próximos 30 dias
- ✅ Alternativas no mesmo dia
- ✅ Informação de quantos dias até o slot

---

### 📊 Melhorias nas APIs Existentes

#### **Agendamentos** (`/api/bookings/`)
- ✅ Validação aprimorada de conflitos
- ✅ Filtros por status, unidade e período
- ✅ Informações detalhadas do massagista

#### **Unidades** (`/api/units/`)
- ✅ Lista todas as unidades disponíveis

#### **Massagistas** (`/api/massagista/`)
- ✅ Filtro por unidade
- ✅ Informações de disponibilidade
- ✅ Avatar padrão

#### **Serviços** (`/api/services/`)
- ✅ Lista todos os serviços com preços

---

## 🔧 Configuração para Produção

### Variáveis de Ambiente Necessárias:

```env
# Email (para esqueci a senha)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-app

# Segurança
SECRET_KEY=sua-chave-secreta-super-forte
```

### Como Usar:

1. **Instalar dependências:**
```bash
pip install fastapi uvicorn sqlalchemy psycopg2 passlib python-jose[cryptography] python-multipart
```

2. **Executar servidor:**
```bash
python app.py
```

3. **Acessar documentação interativa:**
```
http://localhost:8000/docs
```

4. **Testar APIs:**
```bash
python backend/test_api.py
```

---

## 🧪 Testes

O arquivo `test_api.py` testa automaticamente:
- ✅ Todos os endpoints de autenticação
- ✅ Validações de entrada
- ✅ Calendário inteligente
- ✅ Agendamentos
- ✅ Funcionalidades básicas

---

## 🚀 Funcionalidades Implementadas

### ✅ Autenticação Completa
- Registro com validações robustas
- Login seguro com JWT
- Sistema de recuperação de senha
- Alteração de senha
- Atualização de perfil

### ✅ Calendário Inteligente
- Visualização por dia, semana e mês
- Estatísticas detalhadas
- Busca de slots disponíveis
- Análise de padrões

### ✅ Validações de Segurança
- CPF brasileiro
- Força de senha
- Formato de telefone
- Verificação de idade

### ✅ Email Automático
- Template HTML profissional
- Códigos de recuperação
- Fallback para logs em desenvolvimento

### ✅ APIs RESTful
- Códigos de status corretos
- Tratamento de erros
- Documentação automática
- Validação de entrada

---

## 📋 Como Testar

1. **Inicie o servidor:**
```bash
cd backend
python -m uvicorn app.main_simple_render:app --reload --port 8000
```

2. **Execute os testes:**
```bash
python backend/test_api.py
```

3. **Teste manual na documentação:**
- Acesse `http://localhost:8000/docs`
- Use a interface interativa do Swagger

---

## 🎯 Próximos Passos Sugeridos

1. **Integração com WhatsApp** - Notificações automáticas
2. **Sistema de Pagamentos** - Gateway para pagamentos
3. **Dashboard Analytics** - Métricas em tempo real
4. **Sistema de Avaliações** - Feedback dos clientes
5. **Notificações Push** - Lembretes de agendamentos

---

**Desenvolvido com ❤️ para o Espaço VIV** 🌿