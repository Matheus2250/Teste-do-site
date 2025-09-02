# 🚀 Deploy no Render - Espaço VIV

## ✅ **Passo a Passo Simples**

### **1. Preparar Repositório GitHub**

```bash
cd "C:\Users\Matheus Vitorino\Desktop\SITE"

# Inicializar git (se não fez ainda)
git init
git add .
git commit -m "Espaço VIV - Deploy Render"
git branch -M main

# Criar repositório no GitHub e conectar
git remote add origin https://github.com/SEU_USUARIO/espacoviv.git
git push -u origin main
```

### **2. Deploy no Render**

1. **Acesse:** https://render.com/
2. **Cadastre-se/Login** (pode usar conta GitHub)
3. **New → Web Service**
4. **Connect GitHub** → Selecione seu repositório
5. **Configurações:**
   - **Name:** `espacoviv-api`
   - **Region:** Oregon (US West)
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker`

### **3. Variáveis de Ambiente**

No painel do Render, em **Environment**, adicione:

```bash
ENVIRONMENT=production
SECRET_KEY=espacoviv-render-secret-2024-change-this
```

### **4. Clique em "Create Web Service"**

O deploy vai começar automaticamente! ⏱️ ~3-5 minutos

### **5. Testar a API**

Quando terminar, você terá uma URL tipo: `https://espacoviv-api.onrender.com`

**Testar endpoints:**
- https://espacoviv-api.onrender.com/ ✅ Info da API
- https://espacoviv-api.onrender.com/health ✅ Status
- https://espacoviv-api.onrender.com/docs ✅ Documentação
- https://espacoviv-api.onrender.com/api/units ✅ Unidades

---

## 🗄️ **Adicionar PostgreSQL (Opcional)**

### **Opção 1: Render PostgreSQL**
1. **New → PostgreSQL** 
2. **Name:** `espacoviv-db`
3. **Conectar ao Web Service:**
   - No Web Service → Settings → Environment
   - Adicionar: `DATABASE_URL` = `Internal Database URL` do PostgreSQL

**Custo:** $7/mês

### **Opção 2: ElephantSQL (Gratuito)**
1. **Acesse:** https://elephantsql.com/
2. **Create New Instance** (gratuito até 20MB)
3. **Copiar URL** e adicionar como `DATABASE_URL`

### **Opção 3: Supabase (Gratuito)**
1. **Acesse:** https://supabase.com/
2. **New Project**
3. **Settings → Database → Connection String**
4. **Adicionar como** `DATABASE_URL`

---

## 💰 **Custos do Render**

| Serviço | Gratuito | Pago |
|---------|----------|------|
| Web Service | 750h/mês gratuitas* | $7/mês |
| PostgreSQL | ❌ | $7/mês |
| **Total** | **Grátis*** | **$14/mês** |

*Gratuito tem limitações: sleep após inatividade, 750h/mês

---

## 🔧 **Domínio Personalizado**

### **1. Comprar Domínio**
- Registro.br (se .com.br): ~R$ 40/ano
- GoDaddy, Namecheap: ~$12/ano

### **2. Configurar no Render**
1. **Settings → Custom Domains**
2. **Add Custom Domain:** `espacoviv.com`
3. **Configurar DNS:**
   - **A Record:** `216.24.57.1`
   - **CNAME:** `www` → `espacoviv-api.onrender.com`

### **3. SSL Automático**
- Render configura SSL automaticamente
- Nenhuma ação necessária ✅

---

## 📱 **Frontend**

O backend já serve o frontend em `/static/`

**Para testar:**
- https://espacoviv-api.onrender.com/static/pages/index.html

**Para domínio próprio:**
- Configure redirect de `espacoviv.com` → `/static/pages/index.html`

---

## 🔄 **Deploy Automático**

✅ **Configurado:** Push no GitHub = Deploy automático  
✅ **Logs:** Visíveis no painel do Render  
✅ **Rollback:** Histórico de deploys  
✅ **SSL:** Automático  

---

## 🚨 **Troubleshooting**

### **Build Failed:**
- Verificar `requirements.txt`
- Verificar comando de build
- Ver logs no painel

### **App Crashed:**
- Verificar comando de start
- Verificar porta (Render usa variável `$PORT`)
- Ver logs de runtime

### **Database Error:**
- Verificar `DATABASE_URL`
- Confirmar formato: `postgresql://user:pass@host:port/db`

### **CORS Error:**
- Adicionar domínio em `ALLOWED_ORIGINS`
- Verificar protocolo (https)

---

## 📊 **Monitoramento**

### **Render Dashboard:**
- ✅ **CPU/RAM Usage**
- ✅ **Response Time**  
- ✅ **Error Rate**
- ✅ **Deploy History**

### **Logs em Tempo Real:**
```bash
# No painel: Events → View Logs
```

---

## 🎯 **Próximos Passos**

1. ✅ **Deploy básico funcionando**
2. 🔄 **Adicionar PostgreSQL**
3. 🌐 **Configurar domínio**
4. 📱 **Testar frontend**
5. 🔐 **Configurar SSL**
6. 📊 **Monitoramento**

---

## ✨ **Render vs Outras Opções**

| Recurso | Render | Railway | Heroku |
|---------|--------|---------|--------|
| **Facilidade** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Preço** | $7/mês | $5/mês | $7/mês |
| **PostgreSQL** | +$7/mês | Incluso | +$9/mês |
| **SSL** | Grátis | Grátis | Grátis |
| **Domínio** | Fácil | Fácil | Médio |

**Recomendação:** Render é perfeito para começar! 🚀