FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/campo_app_api.py /app/campo_app_api.py

EXPOSE 8010

CMD ["uvicorn", "campo_app_api:app", "--host", "0.0.0.0", "--port", "8010"]
