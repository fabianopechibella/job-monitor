"""
job-monitor · notify.py
Envia e-mail diário com resumo das novas vagas.
Usa SMTP padrão (Gmail App Password ou SendGrid via SMTP).
Variáveis de ambiente: NOTIFY_EMAIL_TO, NOTIFY_EMAIL_FROM, NOTIFY_SMTP_PASS
"""

import os
import json
import smtplib
import logging
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

log = logging.getLogger(__name__)

DATA_FILE   = Path("reports/latest_jobs.json")
REPORT_FILE = Path("reports/report_latest.html")

# ── CONFIG (via env vars no GitHub Actions) ───────────────────────────────────
EMAIL_TO     = os.getenv("NOTIFY_EMAIL_TO",   "fabiano@email.com")
EMAIL_FROM   = os.getenv("NOTIFY_EMAIL_FROM", "jobmonitor@gmail.com")
SMTP_HOST    = os.getenv("NOTIFY_SMTP_HOST",  "smtp.gmail.com")
SMTP_PORT    = int(os.getenv("NOTIFY_SMTP_PORT", "587"))
SMTP_PASS    = os.getenv("NOTIFY_SMTP_PASS",  "")

# ── GITHUB PAGES URL do relatório (opcional) ──────────────────────────────────
REPORT_URL   = os.getenv("REPORT_BASE_URL", "https://a2malagutti.github.io/job-monitor/report_latest.html")

SOURCE_ICONS = {
    "Catho":           "🟠",
    "InfoJobs":        "🔵",
    "Revelo":          "🟣",
    "Wellfound":       "🟤",
    "ATS-Greenhouse":  "🌿",
    "ATS-Lever":       "🔴",
    "ATS-Direct":      "⚙️",
    "ComprasGov":      "🏛️",
    "DOU":             "📋",
}

def build_html_email(jobs: list, new_jobs: list) -> str:
    now       = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    companies = len({j["company"] for j in new_jobs})

    # Linhas de novas vagas
    rows = ""
    for j in new_jobs[:20]:  # máx 20 no e-mail
        icon = SOURCE_ICONS.get(j["source"], "🔗")
        rows += f"""
        <tr>
          <td style="padding:10px 14px;border-bottom:1px solid #eee;font-weight:600;
                     color:#0e4d5c;font-size:13px;white-space:nowrap;">{j['company']}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #eee;font-size:13px;">
            <a href="{j['url']}" style="color:#1a7a8a;text-decoration:none;font-weight:600;">{j['title']}</a>
          </td>
          <td style="padding:10px 14px;border-bottom:1px solid #eee;font-size:11px;
                     color:#6b7c8d;white-space:nowrap;">{j['location']}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #eee;font-size:11px;
                     color:#6b7c8d;white-space:nowrap;">{icon} {j['source']}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #eee;">
            <a href="{j['url']}"
               style="display:inline-block;padding:5px 12px;background:#f5820d;color:#fff;
                      border-radius:5px;font-size:11px;font-weight:700;text-decoration:none;">Ver</a>
          </td>
        </tr>"""

    overflow = ""
    if len(new_jobs) > 20:
        overflow = f'<p style="text-align:center;color:#6b7c8d;font-size:12px;margin-top:12px;">+ {len(new_jobs)-20} vagas no relatório completo.</p>'

    # Resumo por fonte
    by_source = {}
    for j in new_jobs:
        by_source.setdefault(j["source"], 0)
        by_source[j["source"]] += 1

    source_summary = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'font-size:11px;font-weight:600;padding:3px 10px;border-radius:4px;'
        f'background:#f0f3f6;color:#2e4060;border:1px solid #dde3ea;margin:2px;">'
        f'{SOURCE_ICONS.get(src,"🔗")} {src}: {cnt}</span>'
        for src, cnt in by_source.items()
    )

    empty_state = ""
    if not new_jobs:
        empty_state = """
        <div style="text-align:center;padding:40px;color:#6b7c8d;">
          <div style="font-size:32px;margin-bottom:12px;">✅</div>
          <p style="font-weight:600;">Nenhuma vaga nova hoje.</p>
          <p style="font-size:12px;">Todas as vagas já foram vistas em execuções anteriores.</p>
        </div>"""

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f5f6f8;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:700px;margin:32px auto;background:#fff;border-radius:12px;
            overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">

  <!-- header -->
  <div style="background:linear-gradient(135deg,#0d2233 0%,#0e4d5c 100%);padding:32px 36px 24px;">
    <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
                color:#3faebf;margin-bottom:10px;">Job Monitor · a2malagutti</div>
    <h1 style="font-size:24px;font-weight:800;color:#fff;line-height:1.2;margin-bottom:8px;">
      {len(new_jobs)} novas vagas hoje<br>
      <span style="color:#f5820d;">Scrum Master · Agile</span>
    </h1>
    <p style="font-size:13px;color:#94a3b8;margin-bottom:0;">
      {now} · {len(jobs)} total coletadas · {companies} empresas · fontes alternativas
    </p>
  </div>

  <!-- source summary -->
  <div style="padding:16px 36px;background:#f9fafc;border-bottom:1px solid #eee;">
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                letter-spacing:.07em;color:#6b7c8d;margin-bottom:8px;">Por fonte</div>
    <div style="display:flex;flex-wrap:wrap;gap:4px;">{source_summary or '<span style="color:#6b7c8d;font-size:12px;">Nenhuma nova vaga.</span>'}</div>
  </div>

  <!-- vagas -->
  <div style="padding:24px 36px 8px;">
    <h2 style="font-size:14px;font-weight:700;color:#0d2233;
               text-transform:uppercase;letter-spacing:.05em;margin-bottom:16px;">
      Novas vagas detectadas
    </h2>
    {empty_state}
    {"<div style='overflow-x:auto;'><table style='width:100%;border-collapse:collapse;'>" + rows + "</table></div>" if new_jobs else ""}
    {overflow}
  </div>

  <!-- cta -->
  <div style="padding:24px 36px 32px;text-align:center;">
    <a href="{REPORT_URL}"
       style="display:inline-block;padding:13px 32px;background:#f5820d;color:#fff;
              border-radius:8px;font-size:14px;font-weight:700;text-decoration:none;
              letter-spacing:.01em;">
      Ver relatório completo →
    </a>
    <p style="font-size:11px;color:#94a3b8;margin-top:12px;">
      Relatório gerado automaticamente via GitHub Actions.<br>
      Fontes: Catho · InfoJobs · Revelo · Wellfound · ATS Diretos · DOU · ComprasGov
    </p>
  </div>
</div>
</body>
</html>"""

def send_email(subject: str, html_body: str):
    if not SMTP_PASS:
        log.warning("NOTIFY_SMTP_PASS não configurado — e-mail não enviado.")
        log.info(f"Assunto que seria enviado: {subject}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_FROM, SMTP_PASS)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        log.info(f"E-mail enviado para {EMAIL_TO}")
    except Exception as e:
        log.error(f"Erro ao enviar e-mail: {e}")

def main():
    if not DATA_FILE.exists():
        log.error("Arquivo de dados não encontrado. Execute scraper.py e report.py primeiro.")
        return

    jobs     = json.loads(DATA_FILE.read_text())
    new_jobs = [j for j in jobs if j.get("new")]

    now     = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    subject = f"[Job Monitor] {len(new_jobs)} novas vagas Agile — {now}"

    html = build_html_email(jobs, new_jobs)
    send_email(subject, html)

    log.info(f"Notificação: {len(new_jobs)} novas / {len(jobs)} total")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    main()
