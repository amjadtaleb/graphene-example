FROM python:3.12-slim-bookworm AS builder

WORKDIR /venv

RUN apt-get update && apt-get install -y git

RUN pip install uv
# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

COPY ./pyproject.toml /venv/pyproject.toml

RUN uv sync --no-group dev

FROM python:3.12-slim-bookworm AS runner

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /venv /venv
ENV PATH="/venv/.venv/bin:$PATH"

WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--reload"]
