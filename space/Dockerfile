FROM python:3.12.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY space/app.py ./space/app.py
COPY dashboard ./dashboard
COPY bench/results ./bench/results

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --no-create-home app

EXPOSE 7860
USER 10001:10001

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/_stcore/health', timeout=2).read()"]

CMD ["streamlit", "run", "space/app.py", "--server.address=0.0.0.0", "--server.port=7860", "--server.headless=true"]
