# Espaço VIV - Sistema de Agendamento de Massagens

Sistema completo para agendamento de massagens com frontend moderno e backend robusto.

## 📁 Estrutura do Projeto

```
SITE/
├── frontend/                 # Frontend da aplicação
│   ├── pages/               # Páginas HTML
│   │   ├── index.html       # Página principal
│   │   ├── dashboard.html   # Dashboard das massagistas
│   │   ├── promocoes.html   # Página de promoções
│   │   ├── massagens.html   # Página de massagens
│   │   ├── cursos.html      # Página de cursos
│   │   └── unidades/        # Páginas das unidades
│   │       ├── sp.html      # São Paulo
│   │       ├── rj.html      # Rio de Janeiro
│   │       └── bsb.html     # Brasília
│   ├── components/          # Componentes JavaScript
│   │   ├── BookingModal.js  # Modal de agendamento
│   │   └── UserAuth.js      # Autenticação de usuários
│   ├── js/                  # Scripts JavaScript
│   │   └── main.js          # Script principal
│   └── css/                 # Estilos CSS
├── backend/                 # Backend da aplicação
│   ├── app/                 # Aplicação principal
│   │   └── main.py          # Arquivo principal FastAPI
│   ├── models/              # Modelos de dados
│   │   ├── users.py         # Usuários e perfis
│   │   └── bookings.py      # Agendamentos
│   ├── routes/              # Rotas da API
│   │   ├── auth.py          # Autenticação
│   │   ├── bookings.py      # Agendamentos
│   │   ├── massagistas.py   # Massagistas
│   │   └── units.py         # Unidades
│   ├── database/            # Configuração do banco
│   │   ├── connection.py    # Conexão com PostgreSQL
│   │   └── init_database.sql # Script de inicialização
│   └── utils/               # Utilitários
│       └── auth.py          # Funções de autenticação
└── assets/                  # Assets estáticos
    └── images/              # Imagens do site
```

## 🚀 Funcionalidades

### Frontend
- ✅ Sistema de agendamento com 5 passos:
  1. Seleção da unidade
  2. Escolha da massagista
  3. Tipo de serviço
  4. Calendário inteligente
  5. Confirmação
- ✅ Sistema de login para massagistas
- ✅ Dashboard para gerenciar agendamentos
- ✅ Página de promoções com modal de agendamento
- ✅ Design responsivo
- ✅ Componentes JavaScript modulares

### Backend (Python/FastAPI)
- ✅ API RESTful completa
- ✅ Autenticação JWT
- ✅ Sistema de usuários (massagistas)
- ✅ Gerenciamento de agendamentos
- ✅ CRUD de unidades
- ✅ Sistema de disponibilidade
- ✅ Integração com PostgreSQL

## 🛠️ Tecnologias Utilizadas

### Frontend
- HTML5, CSS3, JavaScript (ES6+)
- Font Awesome para ícones
- Google Fonts
- Swiper.js para carrosséis
- Design responsivo com Grid e Flexbox

### Backend
- **Python 3.8+**
- **FastAPI** - Framework web moderno e rápido
- **SQLAlchemy** - ORM para banco de dados
- **PostgreSQL** - Banco de dados principal
- **JWT** - Autenticação por tokens
- **Bcrypt** - Hash de senhas
- **Pydantic** - Validação de dados

## 📦 Instalação e Configuração

### 1. Pré-requisitos
- Python 3.8+
- PostgreSQL 12+
- Node.js (opcional, para desenvolvimento)

### 2. Configuração do Banco de Dados

```sql
-- Criar banco e usuário
CREATE DATABASE espacoviv_db;
CREATE USER espacoviv_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE espacoviv_db TO espacoviv_user;
```

```bash
# Executar script de inicialização
psql -U espacoviv_user -d espacoviv_db -f backend/database/init_database.sql
```

### 3. Configuração do Backend

```bash
# Entrar na pasta do backend
cd backend

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações

# Executar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Configuração do Frontend

O frontend é servido como arquivos estáticos. Para desenvolvimento local:

```bash
# Servir arquivos estáticos (exemplo com Python)
cd frontend
python -m http.server 3000

# Ou usar qualquer servidor web local
```

## 🔗 Endpoints da API

### Autenticação
- `POST /api/auth/register` - Cadastro de massagista
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Dados do usuário atual

### Agendamentos
- `POST /api/bookings` - Criar agendamento
- `GET /api/bookings` - Listar agendamentos
- `GET /api/bookings/{id}` - Detalhes do agendamento
- `PUT /api/bookings/{id}/status` - Atualizar status

### Massagistas
- `GET /api/massagista/by-unit/{unit_code}` - Massagistas por unidade
- `GET /api/massagista/appointments` - Meus agendamentos
- `GET /api/massagista/appointments/calendar` - Calendário
- `PUT /api/massagista/appointments/{id}/status` - Atualizar status

### Unidades
- `GET /api/units` - Listar unidades
- `GET /api/units/{code}` - Detalhes da unidade
- `POST /api/units` - Criar unidade

## 🎯 Sistema de Agendamento

### Fluxo Completo
1. Cliente acessa o site
2. Clica em "Agendar Massagem" ou em promoção
3. Seleciona unidade desejada
4. Escolhe massagista disponível na unidade
5. Seleciona tipo de serviço
6. Escolhe data e horário no calendário inteligente
7. Confirma dados e envia solicitação
8. Massagista recebe notificação no dashboard
9. Massagista confirma ou cancela agendamento

### Estados do Agendamento
- `pending` - Aguardando confirmação
- `confirmed` - Confirmado pela massagista
- `cancelled` - Cancelado
- `completed` - Realizado
- `no_show` - Cliente não compareceu

## Unidades

### São Paulo (4 unidades)
- Ingleses [Matriz] - Bela Vista
- Perdizes - 24h
- Vila Clementino - 24h  
- Prudente de Moraes - 24h

### Rio de Janeiro (2 unidades)
- Centro - Av. Rio Branco
- Copacabana

### Brasília (2 unidades)
- Sudoeste - 24h
- Asa Sul (Galeria Hotel Nacional) - 24h