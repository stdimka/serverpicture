
FROM python:3.13-slim as builder

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости в директорию /install
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


FROM python:3.13-slim

WORKDIR /app

# Установка системных зависимостей для Pillow
RUN apt-get update && \
    apt-get install -y --no-install-recommends libjpeg-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

# Копирую установленные зависимости из builder
COPY --from=builder /install /usr/local

# Копирую исходный код
COPY app.py .

# Копирую статические файлы
COPY static/ /static/

# Создаю папки для изображений и логов
RUN mkdir -p /images /logs

# Открываю порт приложения
EXPOSE 8000

# Запуск приложения
CMD ["python", "app.py"]