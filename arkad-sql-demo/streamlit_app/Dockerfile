# Use Python 3.10 image as the base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the local package
COPY sql-market-agent /app/sql-market-agent

# Copy the requirements (pyproject.toml and poetry.lock) into the container
COPY streamlit_app/pyproject.toml streamlit_app/poetry.lock* /app/

# Install Poetry and dependencies
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Install Supervisor
RUN apt-get update && apt-get install -y supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy supervisord configuration file
COPY streamlit_app/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy the rest of your application's code
COPY streamlit_app/ /app/

# Expose the ports Streamlit and HTTP server will run on
EXPOSE 8501 8000

# Command to run supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
