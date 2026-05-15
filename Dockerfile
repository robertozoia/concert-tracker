FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends tini \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
RUN pip install --upgrade pip \
  && pip install \
      "fastapi>=0.115" \
      "uvicorn[standard]>=0.30" \
      "jinja2>=3.1" \
      "sqlalchemy>=2.0" \
      "pydantic>=2.7" \
      "pydantic-settings>=2.3" \
      "python-multipart>=0.0.9" \
      "bcrypt>=4.1" \
      "itsdangerous>=2.2" \
      "apscheduler>=3.10" \
      "requests>=2.32" \
      "beautifulsoup4>=4.12" \
      "lxml>=5.2"

COPY app /app/app

RUN mkdir -p /app/data

EXPOSE 8090

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
