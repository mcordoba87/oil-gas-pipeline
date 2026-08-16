FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/pozos_api.py /app/pozos_api.py

EXPOSE 8000

CMD ["uvicorn", "pozos_api:app", "--host", "0.0.0.0", "--port", "8000"]
