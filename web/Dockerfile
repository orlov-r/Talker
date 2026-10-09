FROM python:3.11-slim
WORKDIR /app
COPY web/requirements.txt /app/web/requirements.txt
RUN pip install --no-cache-dir -r web/requirements.txt
COPY web /app/web
COPY lessons /app/lessons
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 65534:65534
EXPOSE 8080
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8080", "--threads=4", "web.app:app"]
