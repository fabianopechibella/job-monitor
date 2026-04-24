# job-monitor

Monitoramento automático de vagas **Scrum Master · Agile Master · Agile Coach**
via GitHub Actions — fontes alternativas, sem Gupy, sem motores saturados.

---

## Fontes monitoradas

| Fonte | Tipo | Mecanismo |
|---|---|---|
| **Catho** | Portal BR | Scraping HTML + JSON-LD |
| **InfoJobs** | Portal BR | RSS + Scraping HTML |
| **Revelo** | Tech/Scale-ups | Scraping HTML + JSON-LD |
| **Wellfound** | Startups globais | RSS + Scraping HTML |
| **ATS-Greenhouse** | CI&T, Stefanini | API JSON pública |
| **ATS-Lever** | Totvs | API JSON pública |
| **ATS-Direct** | Accenture, Capgemini, NTT DATA | Scraping ATS |
| **ComprasGov** | Governo Federal | RSS oficial |
| **DOU** | Diário Oficial | API Imprensa Nacional |

---

## Estrutura

```
job-monitor/
├── scraper.py          # coleta de todas as fontes
├── report.py           # gera relatório HTML
├── notify.py           # envia e-mail com digest
├── requirements.txt    # dependências Python
├── reports/
│   ├── seen_jobs.json  # histórico (gerado automaticamente)
│   ├── latest_jobs.json
│   └── report_latest.html
└── .github/
    └── workflows/
        └── monitor.yml # execução diária via GitHub Actions
```

---

## Setup em 5 passos

### 1. Criar repositório no GitHub

```bash
git clone https://github.com/SEU_USUARIO/job-monitor
cd job-monitor
# Copie os arquivos para cá
git add .
git commit -m "feat: job-monitor inicial"
git push
```

### 2. Configurar Secrets no GitHub

Acesse: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Valor |
|---|---|
| `NOTIFY_EMAIL_TO` | seu e-mail de destino |
| `NOTIFY_EMAIL_FROM` | e-mail remetente (Gmail) |
| `NOTIFY_SMTP_HOST` | `smtp.gmail.com` |
| `NOTIFY_SMTP_PORT` | `587` |
| `NOTIFY_SMTP_PASS` | App Password do Gmail* |
| `REPORT_BASE_URL` | `https://SEU_USUARIO.github.io/job-monitor/report_latest.html` |

> **Gmail App Password:** acesse [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords),
> crie um app password para "Mail" e use aqui. Nunca use sua senha principal.

### 3. Ativar GitHub Pages

> **O branch `gh-pages` é criado automaticamente** pelo workflow na primeira execução —
> não é necessário criá-lo manualmente.

**Ordem correta:**

1. Faça o push do projeto no `main`
2. Vá em **Actions → Job Monitor → Run workflow** (disparo manual)
3. O workflow cria o branch `gh-pages` automaticamente se ele não existir
4. Depois da primeira execução: **Settings → Pages → Source: Deploy from branch → Branch: `gh-pages` / root**

O relatório ficará disponível em:
`https://SEU_USUARIO.github.io/job-monitor/report_latest.html`

O `index.html` do `gh-pages` redireciona automaticamente para `report_latest.html`.

### 4. Testar manualmente

**Actions → Job Monitor — Coleta Diária → Run workflow**

Opcionalmente marque "Marcar todas as vagas como novas" para ver o relatório completo.

### 5. Aguardar execução automática

O workflow roda automaticamente de **segunda a sexta às 08h00 BRT**.
Para alterar o horário, edite o cron em `.github/workflows/monitor.yml`:

```yaml
- cron: "0 11 * * 1-5"   # 11 UTC = 08h BRT
```

---

## Adicionar novas empresas (ATS diretos)

Edite a lista `ATS_TARGETS` em `scraper.py`:

```python
# Greenhouse (JSON API)
{
    "name":   "Nome da Empresa",
    "ats":    "Greenhouse",
    "url":    "https://boards-api.greenhouse.io/v1/boards/BOARD_SLUG/jobs?content=true",
    "parser": "greenhouse",
},

# Lever (JSON API)
{
    "name":   "Nome da Empresa",
    "ats":    "Lever",
    "url":    "https://api.lever.co/v0/postings/COMPANY_SLUG?mode=json",
    "parser": "lever",
},
```

Para descobrir o slug: acesse a página de vagas da empresa e inspecione a URL do ATS.

---

## Keywords monitoradas

Edite `KEYWORDS` em `scraper.py`:

```python
KEYWORDS = [
    "scrum master",
    "agile master",
    "agile coach",
    "rte release train engineer",
    "agile transformation",
    "agilista",
]
```

---

## Custo

**Zero.** GitHub Actions oferece 2.000 minutos/mês grátis para repositórios públicos
e 500 minutos/mês para privados. Cada execução leva ~3-5 minutos.
