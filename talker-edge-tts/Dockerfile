FROM python:3.11-slim-bookworm

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
 && python -m edge_tts --version

COPY server.py index.html /app/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 EDGE_TTS_VOICE=ka-GE-EkaNeural
USER 65534:65534
EXPOSE 8080
CMD ["python", "/app/server.py"]
