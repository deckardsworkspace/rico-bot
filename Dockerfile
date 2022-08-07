FROM python:3.10-slim AS dependencies

# Install psycopg2 build dependencies
RUN apt-get update && apt-get install -y libpq-dev build-essential

# Install pip requirements under virtualenv
RUN pip install --upgrade pip
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY requirements.txt .
RUN pip install -r requirements.txt


FROM python:3.10-slim AS main
COPY --from=dependencies /opt/venv /opt/venv
LABEL maintainer="Jared Dantis <jareddantis@gmail.com>"

# Install psycopg2 runtime dependencies
RUN apt-get update && apt-get install -y libpq-dev

# Copy bot files and run bot
COPY . /opt/app
WORKDIR /opt/app
ENV PATH="/opt/venv/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
CMD ["python3", "bot.py"]
