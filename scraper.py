"""
job-monitor · scraper.py
Coleta vagas de múltiplas fontes alternativas ao Indeed/LinkedIn.
Fontes: ATS diretos, RSS públicos, Catho, InfoJobs, Revelo, Wellfound, Gov.
"""

import os
import json
import time
import hashlib
import logging
import requests
import feedparser
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Optional

# ── CONFIG ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

KEYWORDS = [
    "scrum master",
    "agile master",
    "agile coach",
    "rte release train engineer",
    "agile transformation",
    "agilista",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SEEN_FILE = Path("reports/seen_jobs.json")
OUTPUT_FILE = Path("reports/latest_jobs.json")

# ── UTILITIES ─────────────────────────────────────────────────────────────────

def job_id(title: str, company: str, url: str) -> str:
    """Hash único por vaga para controle de deduplicação."""
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{url.strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def load_seen() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()

def save_seen(seen: set):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(list(seen), indent=2))

def is_relevant(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in KEYWORDS)

def fetch(url: str, timeout: int = 12) -> Optional[requests.Response]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        log.warning(f"Fetch error [{url}]: {e}")
        return None

def make_job(title, company, location, url, source, mode="–", date=None, extra_tags=None):
    return {
        "id":       job_id(title, company, url),
        "title":    title.strip(),
        "company":  company.strip(),
        "location": location.strip(),
        "url":      url.strip(),
        "source":   source,
        "mode":     mode,
        "date":     date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "tags":     extra_tags or [],
        "new":      True,
    }

# ── FONTE 1: RSS PÚBLICOS ──────────────────────────────────────────────────────

RSS_FEEDS = [
    # InfoJobs BR – busca salva por cargo
    {
        "name": "InfoJobs",
        "url":  "https://www.infojobs.com.br/vagas-de-emprego/scrum-master.aspx?rss=1",
    },
    {
        "name": "InfoJobs",
        "url":  "https://www.infojobs.com.br/vagas-de-emprego/agile-coach.aspx?rss=1",
    },
    # Wellfound / AngelList – tag agile
    {
        "name": "Wellfound",
        "url":  "https://wellfound.com/jobs.rss?role=scrum-master",
    },
    {
        "name": "Wellfound",
        "url":  "https://wellfound.com/jobs.rss?role=agile-coach",
    },
    # Portal de Compras Gov – licitações com "ágil" / "scrum"
    {
        "name": "ComprasGov",
        "url":  "https://www.gov.br/compras/rss/licitacoes.rss",
    },
    # Diário Oficial da União – busca por "scrum"
    {
        "name": "DOU",
        "url":  "https://www.in.gov.br/servicos/busca-de-publicacoes?q=scrum+master&s=todos&exactDate=personalizado&startDate=&endDate=&currentPage=1&pageSize=20&orgPrin=&orgSub=&artType=&format=rss",
    },
    {
        "name": "DOU",
        "url":  "https://www.in.gov.br/servicos/busca-de-publicacoes?q=agile+coach&s=todos&exactDate=personalizado&startDate=&endDate=&currentPage=1&pageSize=20&orgPrin=&orgSub=&artType=&format=rss",
    },
]

def scrape_rss_feeds() -> list:
    jobs = []
    for feed_cfg in RSS_FEEDS:
        log.info(f"RSS → {feed_cfg['name']}: {feed_cfg['url'][:60]}...")
        try:
            feed = feedparser.parse(feed_cfg["url"])
            for entry in feed.entries:
                title    = entry.get("title", "")
                url      = entry.get("link", "")
                summary  = entry.get("summary", "")
                company  = entry.get("author", feed_cfg["name"])
                location = "Brasil"

                if not is_relevant(title) and not is_relevant(summary):
                    continue

                jobs.append(make_job(
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    source=feed_cfg["name"],
                    date=entry.get("published", "")[:10] if entry.get("published") else None,
                ))
        except Exception as e:
            log.warning(f"RSS error [{feed_cfg['name']}]: {e}")
        time.sleep(1)
    return jobs

# ── FONTE 2: CATHO ────────────────────────────────────────────────────────────

CATHO_SEARCHES = [
    "scrum-master",
    "agile-coach",
    "agile-master",
]

def scrape_catho() -> list:
    jobs = []
    base = "https://www.catho.com.br/vagas/{kw}/"
    for kw in CATHO_SEARCHES:
        url = base.format(kw=kw)
        log.info(f"Catho → {url}")
        r = fetch(url)
        if not r:
            continue
        soup = BeautifulSoup(r.text, "html.parser")

        # Catho usa JSON-LD estruturado em algumas páginas
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string or "{}")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") != "JobPosting":
                        continue
                    title   = item.get("title", "")
                    company = item.get("hiringOrganization", {}).get("name", "Não informado")
                    loc     = item.get("jobLocation", {})
                    address = loc.get("address", {})
                    city    = address.get("addressLocality", "Brasil")
                    job_url = item.get("url", url)
                    date    = item.get("datePosted", "")[:10]
                    mode    = item.get("jobLocationType", "–")

                    if not is_relevant(title):
                        continue
                    jobs.append(make_job(title, company, city, job_url, "Catho", mode, date))
            except Exception:
                pass

        # Fallback: scraping de cards HTML
        cards = soup.select("article[data-testid], div[class*='job-card'], li[class*='JobCard']")
        for card in cards:
            try:
                t_el  = card.select_one("h2 a, h3 a, [class*='title'] a")
                c_el  = card.select_one("[class*='company'], [class*='employer']")
                l_el  = card.select_one("[class*='location'], [class*='city']")
                if not t_el:
                    continue
                title   = t_el.get_text(strip=True)
                href    = t_el.get("href", "")
                job_url = href if href.startswith("http") else "https://www.catho.com.br" + href
                company = c_el.get_text(strip=True) if c_el else "Não informado"
                loc     = l_el.get_text(strip=True) if l_el else "Brasil"

                if not is_relevant(title):
                    continue
                jobs.append(make_job(title, company, loc, job_url, "Catho"))
            except Exception:
                pass

        time.sleep(2)
    return jobs

# ── FONTE 3: INFOJOBS (HTML FALLBACK) ─────────────────────────────────────────

def scrape_infojobs() -> list:
    jobs = []
    searches = ["scrum+master", "agile+coach", "agile+master"]
    base = "https://www.infojobs.com.br/empregos.aspx?palabra={kw}"
    for kw in searches:
        url = base.format(kw=kw)
        log.info(f"InfoJobs → {url}")
        r = fetch(url)
        if not r:
            continue
        soup = BeautifulSoup(r.text, "html.parser")

        # JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data  = json.loads(script.string or "{}")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") != "JobPosting":
                        continue
                    title   = item.get("title", "")
                    company = item.get("hiringOrganization", {}).get("name", "–")
                    city    = item.get("jobLocation", {}).get("address", {}).get("addressLocality", "Brasil")
                    job_url = item.get("url", url)
                    date    = item.get("datePosted", "")[:10]
                    if not is_relevant(title):
                        continue
                    jobs.append(make_job(title, company, city, job_url, "InfoJobs", date=date))
            except Exception:
                pass

        # HTML cards
        cards = soup.select("li.ij-OfferList-item, div[class*='offer'], article")
        for card in cards:
            try:
                t_el = card.select_one("h2 a, h3 a, a[class*='title']")
                c_el = card.select_one("[class*='company'], [class*='employer']")
                l_el = card.select_one("[class*='location']")
                if not t_el:
                    continue
                title   = t_el.get_text(strip=True)
                href    = t_el.get("href", "")
                job_url = href if href.startswith("http") else "https://www.infojobs.com.br" + href
                company = c_el.get_text(strip=True) if c_el else "–"
                loc     = l_el.get_text(strip=True) if l_el else "Brasil"
                if not is_relevant(title):
                    continue
                jobs.append(make_job(title, company, loc, job_url, "InfoJobs"))
            except Exception:
                pass

        time.sleep(2)
    return jobs

# ── FONTE 4: REVELO ───────────────────────────────────────────────────────────

def scrape_revelo() -> list:
    jobs = []
    searches = ["scrum-master", "agile-coach"]
    for kw in searches:
        url = f"https://www.revelo.com.br/vagas/{kw}"
        log.info(f"Revelo → {url}")
        r = fetch(url)
        if not r:
            continue
        soup = BeautifulSoup(r.text, "html.parser")

        # JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data  = json.loads(script.string or "{}")
                items = data if isinstance(data, list) else data.get("@graph", [data])
                for item in items:
                    if item.get("@type") != "JobPosting":
                        continue
                    title   = item.get("title", "")
                    company = item.get("hiringOrganization", {}).get("name", "–")
                    loc_raw = item.get("jobLocation", {})
                    city    = loc_raw.get("address", {}).get("addressLocality", "Brasil") if isinstance(loc_raw, dict) else "Brasil"
                    job_url = item.get("url", url)
                    date    = item.get("datePosted", "")[:10]
                    mode    = "Remote" if item.get("jobLocationType") == "TELECOMMUTE" else "–"
                    if not is_relevant(title):
                        continue
                    jobs.append(make_job(title, company, city, job_url, "Revelo", mode, date))
            except Exception:
                pass

        # HTML fallback
        cards = soup.select("[class*='job-card'], [class*='JobCard'], article")
        for card in cards:
            try:
                t_el = card.select_one("h2 a, h3 a, [class*='title'] a")
                c_el = card.select_one("[class*='company']")
                l_el = card.select_one("[class*='location']")
                if not t_el:
                    continue
                title   = t_el.get_text(strip=True)
                href    = t_el.get("href", "")
                job_url = href if href.startswith("http") else "https://www.revelo.com.br" + href
                company = c_el.get_text(strip=True) if c_el else "–"
                loc     = l_el.get_text(strip=True) if l_el else "Brasil"
                if not is_relevant(title):
                    continue
                jobs.append(make_job(title, company, loc, job_url, "Revelo"))
            except Exception:
                pass

        time.sleep(2)
    return jobs

# ── FONTE 5: WELLFOUND ────────────────────────────────────────────────────────

def scrape_wellfound() -> list:
    """Wellfound tem RSS por role — complementado com scraping de página."""
    jobs = []
    roles = ["scrum-master", "agile-coach", "agile-master"]
    for role in roles:
        url = f"https://wellfound.com/role/r/{role}?country=brazil"
        log.info(f"Wellfound → {url}")
        r = fetch(url)
        if not r:
            continue
        soup = BeautifulSoup(r.text, "html.parser")

        # JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data  = json.loads(script.string or "{}")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") != "JobPosting":
                        continue
                    title   = item.get("title", "")
                    company = item.get("hiringOrganization", {}).get("name", "–")
                    city    = item.get("jobLocation", {}).get("address", {}).get("addressLocality", "Brasil")
                    job_url = item.get("url", url)
                    date    = item.get("datePosted", "")[:10]
                    mode    = "Remote" if "TELECOMMUTE" in str(item.get("jobLocationType", "")) else "–"
                    if not is_relevant(title):
                        continue
                    jobs.append(make_job(title, company, city, job_url, "Wellfound", mode, date))
            except Exception:
                pass

        time.sleep(2)
    return jobs

# ── FONTE 6: ATS DIRETOS ──────────────────────────────────────────────────────
# Workday, Greenhouse, Lever — cada empresa tem endpoint JSON próprio.

ATS_TARGETS = [
    # Greenhouse
    {
        "name":    "CI&T",
        "ats":     "Greenhouse",
        "url":     "https://boards-api.greenhouse.io/v1/boards/ciandt/jobs?content=true",
        "parser":  "greenhouse",
    },
    {
        "name":    "Stefanini",
        "ats":     "Greenhouse",
        "url":     "https://boards-api.greenhouse.io/v1/boards/stefanini/jobs?content=true",
        "parser":  "greenhouse",
    },
    # Lever
    {
        "name":    "Totvs",
        "ats":     "Lever",
        "url":     "https://api.lever.co/v0/postings/totvs?mode=json",
        "parser":  "lever",
    },
    # Workday — endpoint JSON discovery pattern
    # Workday não tem API pública uniforme; usamos scraping de página de busca.
    {
        "name":    "Accenture Brasil",
        "ats":     "Workday-scrape",
        "url":     "https://www.accenture.com/br-pt/careers/jobsearch?jk=scrum+master&sb=1&pg=1&is_rj=0&ct=br",
        "parser":  "html-generic",
    },
    {
        "name":    "Capgemini Brasil",
        "ats":     "Taleo-scrape",
        "url":     "https://www.capgemini.com/br-pt/careers/job-search/?search=scrum+master&country=BR",
        "parser":  "html-generic",
    },
    {
        "name":    "NTT DATA",
        "ats":     "SuccessFactors-scrape",
        "url":     "https://careers.nttdata.com/global/en/search-results?keywords=scrum+master&country=Brazil",
        "parser":  "html-generic",
    },
]

def parse_greenhouse(data: dict, company: str) -> list:
    jobs = []
    for job in data.get("jobs", []):
        title   = job.get("title", "")
        if not is_relevant(title):
            continue
        loc     = job.get("location", {}).get("name", "Brasil")
        url     = job.get("absolute_url", "")
        date    = job.get("updated_at", "")[:10]
        jobs.append(make_job(title, company, loc, url, "ATS-Greenhouse", date=date))
    return jobs

def parse_lever(entries: list, company: str) -> list:
    jobs = []
    for entry in entries:
        title   = entry.get("text", "")
        if not is_relevant(title):
            continue
        loc     = entry.get("categories", {}).get("location", "Brasil")
        url     = entry.get("hostedUrl", "")
        date    = datetime.fromtimestamp(
            entry.get("createdAt", 0) / 1000, tz=timezone.utc
        ).strftime("%Y-%m-%d")
        jobs.append(make_job(title, company, loc, url, "ATS-Lever", date=date))
    return jobs

def parse_html_generic(r: requests.Response, company: str, source_url: str) -> list:
    jobs = []
    soup = BeautifulSoup(r.text, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data  = json.loads(script.string or "{}")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") != "JobPosting":
                    continue
                title   = item.get("title", "")
                if not is_relevant(title):
                    continue
                city    = item.get("jobLocation", {}).get("address", {}).get("addressLocality", "Brasil")
                url     = item.get("url", source_url)
                date    = item.get("datePosted", "")[:10]
                jobs.append(make_job(title, company, city, url, "ATS-Direct", date=date))
        except Exception:
            pass
    return jobs

def scrape_ats_direct() -> list:
    jobs = []
    for target in ATS_TARGETS:
        log.info(f"ATS → {target['name']} ({target['ats']}): {target['url'][:60]}...")
        r = fetch(target["url"])
        if not r:
            continue
        try:
            if target["parser"] == "greenhouse":
                jobs += parse_greenhouse(r.json(), target["name"])
            elif target["parser"] == "lever":
                jobs += parse_lever(r.json(), target["name"])
            else:
                jobs += parse_html_generic(r, target["name"], target["url"])
        except Exception as e:
            log.warning(f"ATS parse error [{target['name']}]: {e}")
        time.sleep(1.5)
    return jobs

# ── FONTE 7: PORTAL COMPRAS GOV (API IMPRENSA NACIONAL) ──────────────────────

def scrape_dou_api() -> list:
    """API pública da Imprensa Nacional — busca no DOU por termos ágeis."""
    jobs = []
    terms = ["scrum master", "agile coach", "metodologia ágil"]
    base  = "https://www.in.gov.br/servicos/busca-de-publicacoes?q={q}&format=json&pageSize=10"
    for term in terms:
        url = base.format(q=requests.utils.quote(term))
        log.info(f"DOU API → '{term}'")
        r = fetch(url)
        if not r:
            continue
        try:
            data  = r.json()
            items = data.get("items", [])
            for item in items:
                title   = item.get("title", "")
                summary = item.get("content", "")
                if not is_relevant(title) and not is_relevant(summary):
                    continue
                pub_url = item.get("href", "https://www.in.gov.br")
                date    = item.get("pubDate", "")[:10]
                jobs.append(make_job(
                    title=title or f"DOU: {term}",
                    company="Governo Federal",
                    location="Brasil",
                    url=pub_url,
                    source="DOU",
                    date=date,
                    extra_tags=["Gov", "Licitação"],
                ))
        except Exception as e:
            log.warning(f"DOU API error: {e}")
        time.sleep(1)
    return jobs

# ── MAIN ──────────────────────────────────────────────────────────────────────

def deduplicate(jobs: list) -> list:
    seen_ids = {}
    for j in jobs:
        if j["id"] not in seen_ids:
            seen_ids[j["id"]] = j
    return list(seen_ids.values())

def mark_new(jobs: list, seen: set) -> tuple[list, set]:
    new_seen = set(seen)
    for j in jobs:
        if j["id"] in seen:
            j["new"] = False
        else:
            j["new"] = True
            new_seen.add(j["id"])
    return jobs, new_seen

def main():
    log.info("═" * 60)
    log.info("job-monitor — iniciando coleta")
    log.info("═" * 60)

    seen = load_seen()
    all_jobs = []

    # ── coleta ──
    all_jobs += scrape_rss_feeds()
    all_jobs += scrape_catho()
    all_jobs += scrape_infojobs()
    all_jobs += scrape_revelo()
    all_jobs += scrape_wellfound()
    all_jobs += scrape_ats_direct()
    all_jobs += scrape_dou_api()

    # ── dedup + novidades ──
    all_jobs          = deduplicate(all_jobs)
    all_jobs, new_seen = mark_new(all_jobs, seen)

    # ── salva ──
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(all_jobs, ensure_ascii=False, indent=2))
    save_seen(new_seen)

    new_count = sum(1 for j in all_jobs if j["new"])
    log.info(f"Coleta concluída: {len(all_jobs)} vagas total | {new_count} novas")
    return all_jobs

if __name__ == "__main__":
    main()
