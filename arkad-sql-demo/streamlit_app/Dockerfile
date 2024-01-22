# Use Python 3.10 image as the base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the local package
COPY sql-market-agent /app/sql-market-agent

# Copy the requirements (pyproject.toml and poetry.lock) into the container
# Ensure the paths are correct relative to the build context
COPY streamlit_app/pyproject.toml streamlit_app/poetry.lock* /app/

# Install Poetry and dependencies
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the rest of your application's code
# Make sure to copy only the necessary files from streamlit_app
COPY streamlit_app/ /app/

# Expose the port Streamlit will run on
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "app.py"]
