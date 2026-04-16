# Playwright ka official Python image — Chromium already included
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Dependencies pehle install karo (cache ke liye)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chromium browser install karo
RUN playwright install chromium

# Baaki code copy karo
COPY . .

# Output folder banana
RUN mkdir -p output

EXPOSE 5000

CMD ["python", "app.py"]
