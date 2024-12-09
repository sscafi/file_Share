import http.server
import socketserver
import os
import urllib.parse
import zipfile
import io

PORT = 8010
desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'OneDrive')
upload_dir = os.path.join(desktop, 'uploads')
os.makedirs(upload_dir, exist_ok=True)  # Create upload directory if it doesn't exist
os.chdir(upload_dir)

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload':
            # Handle file upload
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            boundary = self.headers['Content-Type'].split("=")[1].encode()
            parts = post_data.split(boundary)

            for part in parts:
                if b'filename=' in part:
                    # Extract filename
                    filename = part.split(b'filename=')[1].split(b'\r\n')[0].strip(b'"')
                    filename = os.path.join(upload_dir, filename.decode())
                    with open(filename, 'wb') as f:
                        f.write(part.split(b'\r\n\r\n')[1].split(b'\r\n')[0])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Files uploaded successfully!')
            return

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
                <html>
                <body>
                    <h1>Upload Files</h1>
                    <form action="/upload" method="post" enctype="multipart/form-data">
                        <input type="file" name="file" multiple>
                        <input type="submit" value="Upload">
                    </form>
                    <h1>Download Files</h1>
                    <form action="/download" method="get">
                        <input type="submit" value="Download All Files as ZIP">
                    </form>
                </body>
                </html>
            ''')
        elif self.path == '/download':
            # Create a zip file of all uploaded files
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                for foldername, subfolders, filenames in os.walk(upload_dir):
                    for filename in filenames:
                        file_path = os.path.join(foldername, filename)
                        zip_file.write(file_path, os.path.relpath(file_path, upload_dir))
            zip_buffer.seek(0)

            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', 'attachment; filename=uploaded_files.zip')
            self.end_headers()
            self.wfile.write(zip_buffer.read())
            return
        else:
            super().do_GET()

with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()
