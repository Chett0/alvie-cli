FROM python:3.12-slim

WORKDIR /app

COPY alvie-web/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alvie-web/backend/app ./app

RUN mkdir -p /data
ENV DATABASE_URL=sqlite:////data/alvie.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
