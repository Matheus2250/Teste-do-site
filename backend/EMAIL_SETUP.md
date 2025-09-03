# 📧 Configuração de Email - Espaço VIV

Este documento explica como configurar o sistema de envio de emails para produção.

## 🚀 Configuração para Produção

### 1. Variáveis de Ambiente (arquivo `.env`)

```bash
# Email Configuration - IMPORTANTE: Configure com suas credenciais reais
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=contato@espacoviv.com
SMTP_PASSWORD=sua_senha_de_aplicativo_aqui
EMAIL_FROM_NAME=Espaco VIV
EMAIL_REPLY_TO=noreply@espacoviv.com
EMAIL_ENABLED=true
```

### 2. Como Obter Senha de Aplicativo (Gmail)

1. **Acesse sua Conta Google:** https://myaccount.google.com/
2. **Segurança** → **Verificação em duas etapas** (ative se necessário)
3. **Senhas de aplicativo**
4. **Selecione:** "Outro (nome personalizado)"
5. **Digite:** "Espaco VIV API"
6. **Copie a senha de 16 caracteres** gerada
7. **Use no `SMTP_PASSWORD`**

### 3. Outros Provedores de Email

#### **Outlook/Hotmail:**
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=seu_email@outlook.com
SMTP_PASSWORD=sua_senha
```

#### **Yahoo Mail:**
```bash
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USER=seu_email@yahoo.com
SMTP_PASSWORD=sua_senha_de_aplicativo
```

#### **Provedor Personalizado:**
```bash
SMTP_SERVER=mail.seudominio.com
SMTP_PORT=587  # ou 465 para SSL
SMTP_USER=contato@seudominio.com
SMTP_PASSWORD=sua_senha
```

## ⚙️ Configurações Avançadas

### Desabilitar Email Temporariamente
```bash
EMAIL_ENABLED=false
```

### Logs de Monitoramento
O sistema gera logs automáticos:
- `[EMAIL] Sistema de email configurado e ativado`
- `[EMAIL] Email de redefinicao enviado com sucesso para usuario@email.com`
- `[EMAIL] ERRO: Falha na autenticacao SMTP`

## 🔐 Segurança

### ⚠️ IMPORTANTE:
- **Nunca** commit credenciais no repositório
- Use senhas de aplicativo, não senhas normais
- Mantenha o arquivo `.env` no `.gitignore`
- Use emails dedicados para o sistema (ex: `noreply@espacoviv.com`)

### .gitignore
Adicione estas linhas ao seu `.gitignore`:
```
.env
.env.local
.env.production
*.env
```

## 🧪 Teste da Configuração

### 1. Verificar Status na Inicialização
Ao iniciar o servidor, você deve ver:
```
[EMAIL] Sistema de email configurado e ativado
[EMAIL] Servidor SMTP: smtp.gmail.com
[EMAIL] Usuario: contato@espacoviv.com
```

### 2. Testar Envio
```bash
curl -X POST "http://localhost:10000/api/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario_teste@gmail.com"}'
```

### 3. Verificar Logs
No console do servidor, procure por:
- `[EMAIL] Email de redefinicao enviado com sucesso`
- Ou mensagens de erro específicas

## 🔧 Solução de Problemas

### Erro: "Falha na autenticacao SMTP"
- Verifique se a senha de aplicativo está correta
- Confirme se a verificação em duas etapas está ativada
- Teste com outro provedor de email

### Erro: "Configuracao incompleta"
- Verifique se `SMTP_USER` e `SMTP_PASSWORD` estão preenchidos
- Confirme se `EMAIL_ENABLED=true`

### Email não está chegando
- Verifique a pasta de SPAM/Lixo eletrônico
- Confirme se o email do remetente não está bloqueado
- Teste com diferentes provedores de email

## 📋 Checklist de Deploy

- [ ] Configurar `.env` com credenciais reais
- [ ] Testar envio em ambiente de desenvolvimento
- [ ] Verificar logs de inicialização
- [ ] Testar funcionalidade "Esqueci minha senha"
- [ ] Confirmar recebimento de emails
- [ ] Configurar monitoramento de logs
- [ ] Adicionar `.env` ao `.gitignore`

## 📞 Suporte

Para problemas com a configuração de email, verifique:
1. Logs do servidor
2. Configurações do provedor de email
3. Firewall/Porta 587 liberada
4. Status da API nos logs

---
*Documentação atualizada em: $(date)*