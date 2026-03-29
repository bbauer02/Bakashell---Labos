FROM python:3.11-slim

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    jinja2 \
    python-multipart \
    docker \
    itsdangerous

COPY app/ /app/app/
COPY templates/ /app/templates/

WORKDIR /app
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
