"""
job-monitor · report.py
Gera relatório HTML diário no mesmo padrão visual das páginas de vagas.
Compatível com Python 3.11+ (sem backslash em f-strings).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DATA_FILE  = Path("reports/latest_jobs.json")
OUTPUT_DIR = Path("reports")

SOURCE_COLORS = {
    "Catho":           ("🟠", "#fff3e0", "#a34d00", "#fde891"),
    "InfoJobs":        ("🔵", "#e8f1ff", "#1a4eaa", "#bdd4ff"),
    "Revelo":          ("🟣", "#f0ebff", "#5b1eaa", "#c4aaff"),
    "Wellfound":       ("🟤", "#fdf3e8", "#7a4200", "#fcd5a0"),
    "ATS-Greenhouse":  ("🌿", "#e6f7f2", "#0d6e54", "#a7e9d3"),
    "ATS-Lever":       ("🔴", "#fff0f0", "#aa1a1a", "#ffb0b0"),
    "ATS-Direct":      ("⚙️",  "#f0f3f6", "#2e4060", "#c0cce0"),
    "ComprasGov":      ("🏛️",  "#e8f5e9", "#1b5e20", "#a5d6a7"),
    "DOU":             ("📋", "#fafafa",  "#444444", "#cccccc"),
}

MODE_BADGE = {
    "Remote":  ("🌐", "#e6f7f2", "#0d6e54", "#a7e9d3"),
    "Hybrid":  ("🏢", "#e8f1ff", "#1a4eaa", "#bdd4ff"),
    "On-site": ("📍", "#fff0e0", "#a34d00", "#ffd6a0"),
    "–":       ("",   "#f0f3f6", "#6b7c8d", "#dde3ea"),
}

MONO = "IBM Plex Mono, monospace"
SANS = "Sora, Segoe UI, sans-serif"


def source_chip(source: str) -> str:
    icon, bg, color, border = SOURCE_COLORS.get(source, ("🔗", "#f0f3f6", "#444", "#ccc"))
    return (
        '<span style="display:inline-flex;align-items:center;gap:4px;'
        f'font-size:10px;font-weight:600;padding:2px 8px;border-radius:4px;'
        f'background:{bg};color:{color};border:1px solid {border};'
        f'font-family:{MONO};">'
        f'{icon} {source}</span>'
    )


def mode_chip(mode: str) -> str:
    icon, bg, color, border = MODE_BADGE.get(mode, MODE_BADGE["–"])
    label = mode if mode != "–" else "N/D"
    return (
        '<span style="display:inline-flex;align-items:center;gap:4px;'
        f'font-size:10px;font-weight:600;padding:2px 8px;border-radius:999px;'
        f'background:{bg};color:{color};border:1px solid {border};'
        f'font-family:{MONO};">'
        f'{icon} {label}</span>'
    )


def new_badge() -> str:
    return (
        '<span style="display:inline-block;font-size:9px;font-weight:700;'
        'padding:1px 6px;border-radius:3px;background:#f5820d;color:#fff;'
        f'margin-left:6px;vertical-align:middle;font-family:{MONO};">NEW</span>'
    )


def tag_chip(tag: str) -> str:
    return (
        f'<span style="display:inline-block;font-size:10px;font-weight:600;'
        f'padding:1px 7px;border-radius:4px;margin:1px 2px 1px 0;'
        f'background:#e8f5ff;color:#0055aa;border:1px solid #b0d8ff;'
        f'font-family:{MONO};">{tag}</span>'
    )


def stat_box(value, label: str) -> str:
    return (
        '<div style="background:#f5f6f8;border-radius:8px;padding:14px 16px;border:1px solid #dde3ea;">'
        f'<div style="font-size:26px;font-weight:800;color:#0d2233;line-height:1;margin-bottom:3px;">{value}</div>'
        f'<div style="font-size:11px;color:#6b7c8d;font-weight:500;">{label}</div>'
        '</div>'
    )


def source_stat_row(src: str, count: int) -> str:
    return (
        '<div style="display:flex;justify-content:space-between;align-items:center;'
        'font-size:12px;padding:5px 0;border-bottom:1px solid #dde3ea;">'
        f'<span style="color:#6b7c8d;">{src}</span>'
        f'<span style="font-weight:600;font-family:{MONO};">{count} vagas</span>'
        '</div>'
    )


def tab_button(src: str, count: int, by_source: dict) -> str:
    icon = SOURCE_COLORS.get(src, ("🔗", "", "", ""))[0]
    # escape single quotes for onclick
    src_esc = src.replace("'", "\\'")
    return (
        f'<button class="tab-btn" data-tab="{src}" '
        f'onclick="switchTab(\'{src_esc}\', this)">'
        f'{icon} {src} ({count})</button>'
    )


def build_rows(jobs: list) -> str:
    if not jobs:
        return (
            '<tr><td colspan="8" style="text-align:center;padding:32px;'
            'color:#6b7c8d;font-style:italic;">Nenhuma vaga encontrada nesta fonte.</td></tr>'
        )
    rows = []
    for i, j in enumerate(jobs, 1):
        new_mark  = new_badge() if j.get("new") else ""
        tags_html = "".join(tag_chip(t) for t in j.get("tags", []))
        date_color = "#0d6e54" if j.get("new") else "#6b7c8d"
        url   = j["url"]
        title = j["title"]
        row = (
            '<tr style="border-bottom:1px solid #dde3ea;" '
            'onmouseover="this.style.background=\'#f7f9fb\'" '
            'onmouseout="this.style.background=\'\'">'
            f'<td style="padding:9px 14px;color:#94a3b8;font-family:{MONO};font-size:11px;width:28px;">{i}</td>'
            f'<td style="padding:9px 14px;font-weight:700;color:#0e4d5c;white-space:nowrap;font-size:12px;">{j["company"]}</td>'
            f'<td style="padding:9px 14px;font-size:13px;font-weight:600;">'
            f'<a href="{url}" target="_blank" style="color:#1a2733;text-decoration:none;" '
            f'onmouseover="this.style.color=\'#1a7a8a\'" onmouseout="this.style.color=\'#1a2733\'">'
            f'{title}</a>{new_mark}</td>'
            f'<td style="padding:9px 14px;color:#6b7c8d;font-size:11.5px;white-space:nowrap;">{j["location"]}</td>'
            f'<td style="padding:9px 14px;">{mode_chip(j.get("mode", "–"))}</td>'
            f'<td style="padding:9px 14px;">{source_chip(j["source"])}</td>'
            f'<td style="padding:9px 14px;font-size:10px;font-family:{MONO};color:{date_color};">{j.get("date", "–")}</td>'
            f'<td style="padding:9px 14px;">{tags_html}'
            f'<a href="{url}" target="_blank" '
            f'style="display:inline-block;padding:5px 14px;background:#0e4d5c;color:#fff;'
            f'border-radius:6px;font-size:11px;font-weight:700;text-decoration:none;'
            f'font-family:{SANS};white-space:nowrap;" '
            f'onmouseover="this.style.background=\'#1a7a8a\'" onmouseout="this.style.background=\'#0e4d5c\'">'
            f'Ver Vaga</a></td>'
            '</tr>'
        )
        rows.append(row)
    return "\n".join(rows)


def build_source_section(source: str, jobs: list) -> str:
    icon, bg, color, border = SOURCE_COLORS.get(source, ("🔗", "#f0f3f6", "#444", "#ccc"))
    new_count = sum(1 for j in jobs if j.get("new"))
    new_label = (
        f'<span style="font-size:11px;color:#f5820d;font-family:{MONO};">+{new_count} novas</span>'
        if new_count else ""
    )
    rows_html = build_rows(jobs)
    th_style  = (
        f'padding:8px 14px;text-align:left;font-size:10px;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.07em;color:#6b7c8d;white-space:nowrap;'
    )
    return (
        '<div style="margin-bottom:32px;">'

        # section header
        f'<div style="display:flex;align-items:center;gap:12px;'
        f'padding:12px 20px;border-radius:8px 8px 0 0;'
        f'background:{bg};border:1.5px solid {border};border-bottom:none;">'
        f'<span style="font-size:15px;">{icon}</span>'
        f'<h2 style="font-size:13px;font-weight:700;color:{color};'
        f'text-transform:uppercase;letter-spacing:.05em;">{source}</h2>'
        f'<span style="margin-left:auto;font-size:11px;font-family:{MONO};'
        f'color:{color};background:{bg};border:1px solid {border};'
        f'padding:2px 9px;border-radius:4px;">{len(jobs)} vagas</span>'
        f'{new_label}'
        '</div>'

        # table
        f'<div style="overflow-x:auto;border:1.5px solid {border};border-top:none;'
        f'border-radius:0 0 8px 8px;box-shadow:0 2px 8px rgba(13,34,51,.05);">'
        f'<table style="width:100%;border-collapse:collapse;font-size:12.5px;font-family:{SANS};">'
        '<thead>'
        '<tr style="background:#f0f3f6;border-bottom:1.5px solid #dde3ea;">'
        f'<th style="{th_style}">#</th>'
        f'<th style="{th_style}">Empresa</th>'
        f'<th style="{th_style}">Cargo</th>'
        f'<th style="{th_style}">Localização</th>'
        f'<th style="{th_style}">Mode</th>'
        f'<th style="{th_style}">Fonte</th>'
        f'<th style="{th_style}">Data</th>'
        f'<th style="{th_style}">Link</th>'
        '</tr>'
        '</thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table>'
        '</div>'
        '</div>'
    )


def render_html(jobs: list) -> str:
    now       = datetime.now(timezone.utc).strftime("%d/%m/%Y as %H:%M UTC")
    total     = len(jobs)
    new_count = sum(1 for j in jobs if j.get("new"))
    companies = len({j["company"] for j in jobs})
    sources   = sorted({j["source"] for j in jobs})

    by_source: dict = {}
    for j in jobs:
        by_source.setdefault(j["source"], []).append(j)

    # pre-build string fragments (no backslash inside f-string expressions)
    all_section      = build_source_section("Todas as Fontes", jobs)
    source_sections  = "".join(
        f'<div id="tab-{src}" class="tab-content">{build_source_section(src, by_source[src])}</div>'
        for src in sources
    )
    source_pills     = "".join(source_chip(s) for s in sources)
    source_stats     = "".join(source_stat_row(s, len(by_source[s])) for s in sources)
    stat_boxes       = "".join([
        stat_box(total,     "Vagas coletadas"),
        stat_box(new_count, "Novas hoje"),
        stat_box(companies, "Empresas unicas"),
        stat_box(len(sources), "Fontes ativas"),
    ])
    tab_buttons      = "".join(
        tab_button(src, len(by_source[src]), by_source) for src in sources
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Monitor - Relatorio {now[:10]}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing:border-box;margin:0;padding:0; }}
  body {{ background:#f5f6f8;color:#1a2733;font-family:Sora,sans-serif;font-size:14px;line-height:1.6; }}
  .tab-btn {{ padding:9px 20px;cursor:pointer;font-size:12px;font-weight:600;color:#6b7c8d;
              border-bottom:2px solid transparent;transition:all .15s;user-select:none;
              background:none;border-top:none;border-left:none;border-right:none;font-family:Sora,sans-serif; }}
  .tab-btn:hover {{ color:#1a2733; }}
  .tab-btn.active {{ color:#0e4d5c;border-bottom-color:#f5820d; }}
  .tab-content {{ display:none; }}
  .tab-content.active {{ display:block; }}
</style>
</head>
<body>

<section style="background:#fff;border-bottom:1px solid #dde3ea;padding:44px 56px 36px;
                display:grid;grid-template-columns:1fr 360px;gap:48px;align-items:start;">
  <div>
    <div style="display:inline-flex;align-items:center;gap:6px;border:1.5px solid #dde3ea;
                border-radius:999px;padding:4px 14px;font-size:11px;font-weight:600;
                color:#0e4d5c;letter-spacing:.04em;text-transform:uppercase;margin-bottom:20px;">
      <span style="width:6px;height:6px;border-radius:50%;background:#f5820d;display:inline-block;"></span>
      Job Monitor - a2malagutti - Fontes Alternativas
    </div>
    <h1 style="font-size:clamp(26px,3.8vw,44px);font-weight:800;color:#0d2233;
               line-height:1.12;letter-spacing:-.03em;margin-bottom:16px;">
      Monitoramento<br>
      <span style="color:#1a7a8a;">automatico</span> de vagas<br>
      Scrum Master - Agile.
    </h1>
    <p style="font-size:14px;color:#6b7c8d;max-width:480px;line-height:1.75;margin-bottom:28px;">
      Coleta diaria de {len(sources)} fontes alternativas - ATS diretos, portais de nicho,
      RSS publicos e Diario Oficial. Sem Gupy. Sem motores saturados. Gerado em {now}.
    </p>
    <div style="display:flex;flex-wrap:wrap;gap:7px;">{source_pills}</div>
  </div>

  <div style="background:#fff;border:1.5px solid #dde3ea;border-radius:12px;
              padding:26px 26px 22px;box-shadow:0 4px 24px rgba(13,34,51,.07);">
    <div style="font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
                color:#6b7c8d;margin-bottom:18px;">Resumo da coleta</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:18px;">
      {stat_boxes}
    </div>
    <div style="margin-bottom:18px;">{source_stats}</div>
    <button onclick="switchTab('Todas as Fontes', document.querySelector('[data-tab=\\'Todas as Fontes\\']'))"
            style="width:100%;padding:13px;background:#f5820d;color:#fff;border:none;
                   border-radius:8px;font-family:Sora,sans-serif;font-size:14px;
                   font-weight:700;cursor:pointer;">
      Ver todas as vagas
    </button>
    <p style="font-size:11px;color:#6b7c8d;text-align:center;margin-top:10px;line-height:1.5;">
      <strong style="color:#1a7a8a;">NEW</strong> = vaga nao vista em execucoes anteriores
    </p>
  </div>
</section>

<div style="background:#fff;border-bottom:1px solid #dde3ea;display:flex;
            position:sticky;top:0;z-index:100;overflow-x:auto;">
  <button class="tab-btn active" data-tab="Todas as Fontes"
          onclick="switchTab('Todas as Fontes', this)">
    Todas ({total})
  </button>
  {tab_buttons}
</div>

<main style="padding:32px 56px 64px;">
  <div id="tab-Todas as Fontes" class="tab-content active">
    {all_section}
  </div>
  {source_sections}
</main>

<script>
function switchTab(id, btn) {{
  document.querySelectorAll('.tab-content').forEach(function(t) {{ t.classList.remove('active'); }});
  document.querySelectorAll('.tab-btn').forEach(function(b) {{ b.classList.remove('active'); }});
  var el = document.getElementById('tab-' + id);
  if (el) el.classList.add('active');
  if (btn) btn.classList.add('active');
  window.scrollTo({{ top: document.querySelector('main').offsetTop - 20, behavior: 'smooth' }});
}}
</script>
</body>
</html>"""


def main():
    if not DATA_FILE.exists():
        print("Arquivo de dados nao encontrado. Execute scraper.py primeiro.")
        sys.exit(1)

    jobs = json.loads(DATA_FILE.read_text())
    html = render_html(jobs)

    date_str    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"report_{date_str}.html"
    output_file.write_text(html, encoding="utf-8")

    latest = OUTPUT_DIR / "report_latest.html"
    latest.write_text(html, encoding="utf-8")

    new_count = sum(1 for j in jobs if j.get("new"))
    print(f"Relatorio gerado: {output_file}")
    print(f"Total: {len(jobs)} vagas | {new_count} novas")
    return str(output_file)


if __name__ == "__main__":
    main()
