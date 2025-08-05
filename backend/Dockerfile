FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /code

COPY --from=builder /opt/venv /opt/venv

COPY ./app /code/app
COPY ./scripts /code/scripts
COPY alembic.ini /code/alembic.ini

ENV PATH="/opt/venv/bin:$PATH"

RUN chmod +x /code/scripts/docker-entrypoint.sh
RUN chmod +x /code/scripts/prestart.sh

EXPOSE 8000

ENTRYPOINT ["/code/scripts/docker-entrypoint.sh"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
