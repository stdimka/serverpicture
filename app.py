import json
import logging
import os
import re

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from db_manager import postgres_config, PostgresManager

# Настройки
HOST = '0.0.0.0'
PORT = 8000

class ImageServer(BaseHTTPRequestHandler):
    db = None  # будет установлено через run()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        page = int(query_params.get('page', [1])[0])

        if path == '/':
            self.serve_file('static/index.html', 'text/html')
        elif path == '/upload.html':
            self.serve_file('static/upload.html', 'text/html')
        elif path == '/images.html':
            self.serve_file('static/images.html', 'text/html')
        elif path == '/favicon.ico':
            self.serve_file('static/favicon.ico', 'image/x-icon')
        elif path.startswith('/static/'):
            filepath = 'static' + path[len('/static'):]
            self.serve_file(filepath, self.get_mime_type(filepath))
        elif path == '/api/get-data':
            total, data = ImageServer.db.get_page_by_page_num(page, is_print=False)
            json_data = {
                "items": [
                    {
                        "id": row[0],
                        "name": row[1],
                        "original_name": row[2],
                        "size": row[3],
                        "uploaded_at": row[4].strftime('%Y-%m-%d %H:%M:%S'),
                        "type": row[5]
                    }
                    for row in data
                ],
                "total": total,
                "page": page,
            }
            self.send_json(json_data)
        else:
            self.send_error(404, 'Not Found')

    def do_POST(self):
        if self.path.startswith("/delete/"):
            match = re.match(r"^/delete/(\d+)/?$", self.path)
            if match:
                image_id = match.group(1)
                try:
                    filename = ImageServer.db.get_id_by_filename(image_id)
                    if not filename:
                        self.send_error(404, "Not found")
                        return

                    file_path = f"/images/{filename}"
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    ImageServer.db.delete_by_id(image_id)

                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"Deleted")
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(f"Error: {e}".encode())
            else:
                self.send_error(400, "Invalid delete URL")
        else:
            self.send_error(404, 'Not Found')

    def serve_file(self, filepath, content_type):
        try:
            with open(filepath, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_error(404, 'Not Found')

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def get_mime_type(self, filename):
        ext = filename.split('.')[-1]
        return {
            'html': 'text/html',
            'css': 'text/css',
            'js': 'application/javascript',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'ico': 'image/x-icon'
        }.get(ext, 'application/octet-stream')

def run(db_object):
    ImageServer.db = db_object
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, ImageServer)
    logging.info('Starting server...')
    httpd.serve_forever()

if __name__ == '__main__':
    with PostgresManager(postgres_config) as pm:
        pm.create_table()
        run(pm)
