import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import logging
from datetime import datetime
import uuid
import mimetypes

# Настройки
HOST = "0.0.0.0"
PORT = 8000
IMAGE_DIR = "/images"
LOG_FILE = "/logs/app.log"
STATIC_DIR = "/static"

# Поддерживаемые MIME-типы
SUPPORTED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif"
}

# Логирование
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(message)s"
)

def log_action(action):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    logging.info(f"{timestamp} {action}")

# Генерация уникального имени файла
def generate_unique_filename(original_name):
    _, ext = os.path.splitext(original_name)
    return f"{uuid.uuid4()}{ext}"

# Проверка MIME-типа
def is_supported_mime(content_type):
    return content_type in SUPPORTED_MIME

class ImageServer(BaseHTTPRequestHandler):
    def _set_response(self, code=200, content_type="application/json"):
        self.send_response(code)
        self.send_header("Content-type", content_type)
        self.end_headers()

    def serve_file(self, file_path, content_type=None):
        try:
            if os.path.isdir(file_path):
                # Если запрашивается директория — не открываем её
                self._set_response(400, "text/html")
                self.wfile.write(b"<h1>Can't open directory</h1>")
                return

            with open(file_path, 'rb') as f:
                self._set_response(200, content_type or "application/octet-stream")
                self.wfile.write(f.read())
        except FileNotFoundError:
            self._set_response(404, "text/html")
            self.wfile.write(b"<h1>404: File Not Found</h1>")

    def do_GET(self):
        if self.path == "/":
            self.serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html")
        elif self.path == "/favicon.ico":
            self.serve_file(os.path.join(STATIC_DIR, "favicon.ico"), "image/x-icon")
        elif self.path.startswith("/upload.html"):
            self.serve_file(os.path.join(STATIC_DIR, "upload.html"), "text/html")
        elif self.path.startswith("/images.html"):
            self.serve_file(os.path.join(STATIC_DIR, "images.html"), "text/html")
        elif self.path == "/api/list-images":
            try:
                images = os.listdir(IMAGE_DIR)
                self._set_response(200, "application/json")
                self.wfile.write(json.dumps(images).encode("utf-8"))
            except Exception as e:
                log_action(f"Ошибка при получении списка изображений: {str(e)}")
                self._set_response(500, "application/json")
                self.wfile.write(json.dumps({"error": "Internal Server Error"}).encode("utf-8"))
        elif self.path == "/images":
            # Редирект на /images/
            self.send_response(301)
            self.send_header("Location", "/images/")
            self.end_headers()
        elif self.path.startswith("/static/"):
            filename = self.path[7:]  # /static/abcd.jpg → abcd.jpg
            file_path = os.path.join(STATIC_DIR, filename)
            if os.path.exists(file_path):
                content_type, _ = mimetypes.guess_type(filename)
                self.serve_file(file_path, content_type or "application/octet-stream")
            else:
                self._set_response(404, "text/html")
                self.wfile.write(b"<h1>404: File not found</h1>")
        elif self.path.startswith("/images/"):
            filename = self.path[8:]
            image_path = os.path.join(IMAGE_DIR, filename)
            if os.path.exists(image_path) and not os.path.isdir(image_path):
                content_type, _ = mimetypes.guess_type(filename)
                self.serve_file(image_path, content_type or "image/*")
            else:
                self._set_response(404, "text/html")
                self.wfile.write(b"<h1>404: Image not found</h1>")
        else:
            self._set_response(404, "text/html")
            self.wfile.write(b"<h1>404: Page Not Found</h1>")

    def do_POST(self):
        if self.path == "/upload":
            content_length = int(self.headers["Content-Length"])
            if content_length > 5 * 1024 * 1024:  # 5 МБ
                self._set_response(413)
                self.wfile.write(json.dumps({"error": "File too large"}).encode("utf-8"))
                log_action("Ошибка: файл превышает 5 МБ.")
                return

            content_type = self.headers.get("Content-Type", "")
            if not is_supported_mime(content_type):
                self._set_response(400)
                self.wfile.write(json.dumps({"error": "Unsupported media type"}).encode("utf-8"))
                log_action(f"Ошибка: неподдерживаемый формат '{content_type}'.")
                return

            file_data = self.rfile.read(content_length)
            original_name = self.headers.get("X-File-Name", "unknown")
            unique_name = generate_unique_filename(original_name)
            file_path = os.path.join(IMAGE_DIR, unique_name)

            with open(file_path, "wb") as f:
                f.write(file_data)

            log_action(f"Успех: изображение '{unique_name}' загружено.")
            self._set_response(200)
            self.wfile.write(json.dumps({"url": f"/images/{unique_name}"}).encode("utf-8"))
        else:
            self._set_response(404)
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

    def do_DELETE(self):
        if self.path.startswith("/api/delete/"):
            filename = self.path[len("/api/delete/"):]
            image_path = os.path.join(IMAGE_DIR, filename)

            if not os.path.exists(image_path):
                log_action(f"Ошибка: попытка удалить несуществующий файл '{filename}'")
                self._set_response(404)
                self.wfile.write(json.dumps({"error": "File not found"}).encode("utf-8"))
                return

            try:
                os.remove(image_path)
                log_action(f"Успех: файл '{filename}' удален.")
                self._set_response(200)
                self.wfile.write(json.dumps({"status": "deleted"}).encode("utf-8"))
            except Exception as e:
                log_action(f"Ошибка при удалении файла '{filename}': {str(e)}")
                self._set_response(500)
                self.wfile.write(json.dumps({"error": "Internal server error"}).encode("utf-8"))
        else:
            self._set_response(400)
            self.wfile.write(json.dumps({"error": "Unknown route for DELETE"}).encode("utf-8"))


if __name__ == "__main__":
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
    if not os.path.exists(STATIC_DIR):
        os.makedirs(STATIC_DIR)

    print(f"Starting server on port {PORT}...")
    server = HTTPServer((HOST, PORT), ImageServer)
    server.serve_forever()