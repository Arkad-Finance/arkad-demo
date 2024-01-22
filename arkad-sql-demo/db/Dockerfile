# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install Poetry
RUN pip install poetry

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the poetry lockfile and pyproject.toml into the container
COPY pyproject.toml poetry.lock* /usr/src/app/

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the rest of your application's code
COPY . /usr/src/app

# Run fetch_data.py when the container launches
CMD ["python", "./scheduler.py"]
