# Como gerar o `google_service_account.json`

Guia passo a passo para criar a Service Account do Google e configurar o acesso à planilha do Google Sheets.

---

## 1. Acesse o Google Cloud Console

Vá para [https://console.cloud.google.com/](https://console.cloud.google.com/) e faça login com sua conta Google.

## 2. Crie um projeto (ou use um existente)

- No topo da página, clique no seletor de projetos
- Clique em **"Novo Projeto"**
- Dê um nome (ex: `finance-analytics`) e clique em **"Criar"**

## 3. Ative as APIs necessárias

Acesse **APIs e Serviços > Biblioteca** ou use os links diretos:

- [Ativar Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
- [Ativar Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)

Clique em **"Ativar"** em cada uma.

## 4. Crie a Service Account

1. Vá para **APIs e Serviços > Credenciais** ([link direto](https://console.cloud.google.com/apis/credentials))
2. Clique em **"+ Criar Credenciais"** → **"Conta de serviço"**
3. Preencha:
   - **Nome**: `finance-analytics-sheets` (ou o que preferir)
   - **ID**: será gerado automaticamente
4. Clique em **"Criar e Continuar"**
5. Em "Conceder acesso ao projeto", pode pular → clique **"Continuar"**
6. Em "Conceder acesso de usuário", pode pular → clique **"Concluído"**

## 5. Gere a chave JSON

1. Na lista de Service Accounts, clique na que você acabou de criar
2. Vá na aba **"Chaves"**
3. Clique em **"Adicionar chave"** → **"Criar nova chave"**
4. Selecione **JSON** e clique em **"Criar"**
5. O arquivo `.json` será baixado automaticamente

## 6. Coloque o arquivo no projeto

Mova o arquivo baixado para:

```
backend/credentials/google_service_account.json
```

## 7. Compartilhe a planilha com a Service Account

> 🔑 **Essa é a parte mais importante!**

1. Abra o arquivo JSON que você baixou
2. Copie o valor do campo `"client_email"` — será algo como:
   ```
   finance-analytics-sheets@seu-projeto.iam.gserviceaccount.com
   ```
3. Abra sua planilha no Google Sheets
4. Clique em **"Compartilhar"** (botão verde no canto superior direito)
5. Cole o `client_email` da Service Account
6. Defina a permissão como **"Editor"** (a API precisa escrever na planilha)
7. Desmarque "Notificar pessoas" e clique em **"Compartilhar"**

## 8. Reinicie o container

Depois de colocar o arquivo e compartilhar a planilha:

```bash
docker-compose down
docker-compose up --build
```

---

## ⚠️ Segurança

- **Nunca** faça commit do arquivo `google_service_account.json` no Git
- Verifique se `credentials/` está no `.gitignore`
- O arquivo `.env` também não deve ser commitado
