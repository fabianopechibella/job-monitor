# substitui o arquivo e faz push
curl -o report.py https://raw.githubusercontent.com/fabianopechibella/job-monitor/refs/heads/main/report.py # ou copie manualmente

git add report.py
git commit -m "fix: backslash em f-string Python 3.11"
git push
