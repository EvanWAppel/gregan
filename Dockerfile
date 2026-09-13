FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Bake the DuckDB warehouse into the image at build time. Railway's release
# phase runs in a throwaway container, so the build must happen here (fetches the
# LA County CSV + city/state/federal ArcGIS + EPA/NOAA/USGS/DWR sources, filters
# each county-wide feed to Glendora, then materializes the dbt marts). The DB
# stays out of git and is rebuilt fresh on every deploy.
COPY . .
# Railway only injects service variables into a Dockerfile RUN if they are
# declared as ARG. CENSUS_API_KEY is a free ACS rate-limit token (not billed);
# .env is dockerignored so the key is never copied from a local file.
ARG CENSUS_API_KEY
ENV CENSUS_API_KEY=$CENSUS_API_KEY
RUN dbt deps && python build_warehouse.py && dbt build --profiles-dir .

# Railway injects $PORT at runtime; default to 8501 for local runs. JSON exec
# form so Streamlit gets SIGTERM; sh -c so $PORT still expands.
EXPOSE 8501
CMD ["sh", "-c", "streamlit run streamlit_app.py --server.port ${PORT:-8501} --server.address 0.0.0.0"]
