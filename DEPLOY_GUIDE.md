# 🚀 Guia Completo de Deploy - Espaço VIV

## 📋 Pré-requisitos
- [ ] Conta no GitHub
- [ ] Conta no Railway (gratuito)
- [ ] Domínio próprio (opcional)

## 🎯 Opção 1: Railway (Recomendado - Mais Fácil)

### 1. Preparar GitHub
```bash
# 1. Criar repositório no GitHub (público ou privado)
# 2. Fazer upload dos arquivos

cd "C:\Users\Matheus Vitorino\Desktop\SITE"
git init
git add .
git commit -m "Initial commit - Espaço VIV"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/espacoviv.git
git push -u origin main
```

### 2. Deploy no Railway

**Passo a Passo:**

1. **Acesse:** https://railway.app/
2. **Login com GitHub**
3. **New Project → Deploy from GitHub repo**
4. **Selecione seu repositório**
5. **Railway vai detectar automaticamente o Python**

**Configurar Variáveis de Ambiente:**
```bash
ENVIRONMENT=production
SECRET_KEY=sua-chave-super-secreta-mude-isso-123456789
ALLOWED_ORIGINS=https://espacoviv.railway.app,https://espacoviv.com
```

### 3. Adicionar PostgreSQL
1. **No painel do Railway**
2. **Add Service → PostgreSQL**
3. **Railway vai conectar automaticamente**

### 4. Configurar Domínio Customizado (Opcional)
1. **Settings → Domains**
2. **Custom Domain → Adicionar seu domínio**
3. **Configurar DNS** (CNAME para railway.app)

**Custo:** $5/mês (inclui banco PostgreSQL)

---

## 🎯 Opção 2: DigitalOcean (Mais Controle)

### 1. Criar Droplet
- **Ubuntu 22.04 LTS**
- **Tamanho:** $4-6/mês (1GB RAM)

### 2. Configurar Servidor
```bash
# SSH no servidor
ssh root@seu-servidor-ip

# Atualizar sistema
apt update && apt upgrade -y

# Instalar Python e dependências
apt install python3 python3-pip postgresql postgresql-contrib nginx certbot python3-certbot-nginx -y

# Criar usuário para aplicação
adduser espacoviv
usermod -aG sudo espacoviv
```

### 3. Configurar PostgreSQL
```bash
sudo -u postgres psql

CREATE DATABASE espacoviv_db;
CREATE USER espacoviv_user WITH ENCRYPTED PASSWORD 'sua_senha_segura';
GRANT ALL PRIVILEGES ON DATABASE espacoviv_db TO espacoviv_user;
\q
```

### 4. Deploy da Aplicação
```bash
# Como usuário espacoviv
su espacoviv
cd /home/espacoviv

# Clone o repositório
git clone https://github.com/SEU_USUARIO/espacoviv.git
cd espacoviv/backend

# Instalar dependências
pip3 install -r requirements_production.txt

# Configurar variáveis de ambiente
cp .env.production .env
# Editar com dados reais

# Rodar migrações
python3 app/main_production.py
```

### 5. Configurar Nginx
```bash
sudo nano /etc/nginx/sites-available/espacoviv

# Adicionar configuração (ver arquivo separado)

sudo ln -s /etc/nginx/sites-available/espacoviv /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. SSL Gratuito
```bash
sudo certbot --nginx -d espacoviv.com -d www.espacoviv.com
```

**Custo:** $6/mês + $15/mês banco = $21/mês total

---

## 🎯 Opção 3: Heroku (Mais Caro)

### 1. Install Heroku CLI
https://devcenter.heroku.com/articles/heroku-cli

### 2. Deploy
```bash
cd "C:\Users\Matheus Vitorino\Desktop\SITE"

# Login
heroku login

# Criar app
heroku create espacoviv-app

# Adicionar PostgreSQL
heroku addons:create heroku-postgresql:mini

# Configurar variáveis
heroku config:set ENVIRONMENT=production
heroku config:set SECRET_KEY=sua-chave-secreta

# Deploy
git push heroku main
```

**Custo:** $7/mês app + $9/mês banco = $16/mês

---

## ✅ Checklist Final

### Antes do Deploy:
- [ ] Código no GitHub
- [ ] Variáveis de ambiente configuradas
- [ ] SECRET_KEY alterado
- [ ] Domínio configurado (se tiver)

### Depois do Deploy:
- [ ] Testar endpoints da API
- [ ] Verificar conexão com banco
- [ ] Testar sistema de login
- [ ] Testar agendamentos
- [ ] Configurar SSL
- [ ] Testar no mobile

### URLs para Testar:
- **API:** https://seu-dominio.com/health
- **Documentação:** https://seu-dominio.com/docs
- **Frontend:** https://seu-dominio.com/static/pages/

---

## 🔧 Troubleshooting

### Erro de Conexão com Banco:
```bash
# Verificar variável DATABASE_URL
heroku config:get DATABASE_URL  # Heroku
# ou verificar no painel do Railway
```

### Erro 500:
```bash
# Ver logs
heroku logs --tail  # Heroku
# ou ver logs no painel do Railway
```

### CORS Error:
- Verificar ALLOWED_ORIGINS nas variáveis de ambiente
- Adicionar domínio correto

---

## 💰 Resumo de Custos

| Opção | Backend + DB | Domínio | SSL | Total/mês |
|-------|-------------|----------|-----|-----------|
| Railway | $5 | $10-15 | Grátis | $15-20 |
| DigitalOcean | $21 | $10-15 | Grátis | $31-36 |
| Heroku | $16 | $10-15 | Grátis | $26-31 |

**Recomendação:** Comece com Railway, é mais fácil e barato!