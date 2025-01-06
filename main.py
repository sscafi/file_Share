import http.server
import socketserver
import os
import urllib.parse
import zipfile
import io
from PIL import Image  # Import the Pillow library for image manipulation

PORT = 8010

# Set the path for the file storage
upload_dir = r"C:\Users\saher\OneDrive\Desktop\projects\fileShare\uploads"

# Make sure the upload directory exists
os.makedirs(upload_dir, exist_ok=True)  # Create the uploads directory if it doesn't exist
os.chdir(upload_dir)

# Function to convert all PNG files to JPEG
def convert_png_to_jpeg():
    for filename in os.listdir(upload_dir):
        if filename.lower().endswith('.png'):
            png_path = os.path.join(upload_dir, filename)
            jpg_path = os.path.splitext(png_path)[0] + '.jpg'

            try:
                # Try opening the PNG file with Pillow to check if it's valid
                with Image.open(png_path) as img:
                    img.verify()  # Verify that the image is valid
                    img = Image.open(png_path)  # Re-open the image after verifying it
                    img = img.convert('RGB')  # Convert to RGB (removes alpha channel if any)
                    img.save(jpg_path, 'JPEG')  # Save the image as JPEG
                    print(f"Converted {filename} to {os.path.basename(jpg_path)}")

                # Optionally delete the original PNG file after conversion
                os.remove(png_path)
                print(f"Deleted the original PNG file: {filename}")

            except Exception as e:
                # Log the error with the specific file causing the issue
                print(f"Error converting {filename}: {e}")

# Call the conversion function when the server starts
convert_png_to_jpeg()

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
                    try:
                        # Extract filename
                        filename = part.split(b'filename=')[1].split(b'\r\n')[0].strip(b'"')
                        filename = os.path.join(upload_dir, filename.decode())  # Set the file path to the new directory

                        # Save the file correctly in binary mode
                        with open(filename, 'wb') as f:
                            file_data = part.split(b'\r\n\r\n')[1].split(b'\r\n')[0]
                            f.write(file_data)

                        print(f"File {filename} uploaded successfully.")  # Debugging output

                    except Exception as e:
                        print(f"Error while saving file: {e}")  # If an error occurs during file saving

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
                <head>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body { font-family: Arial, sans-serif; padding: 20px; }
                        h1 { text-align: center; }
                        form { margin-bottom: 20px; }
                        input[type="file"], input[type="submit"] { width: 100%; padding: 10px; margin: 10px 0; }
                        @media (min-width: 600px) {
                            input[type="file"], input[type="submit"] { width: auto; }
                        }
                        img { max-width: 100%; height: auto; }
                    </style>
                </head>
                <body>
                    <h1>File Sharing Service</h1>
                    <h2>Upload Files</h2>
                    <form action="/upload" method="post" enctype="multipart/form-data">
                        <input type="file" name="file" multiple>
                        <input type="submit" value="Upload">
                    </form>
                    <h2>View Uploaded Files</h2>
                    <h3>Images</h3>
                    <div>
            ''')

            # List uploaded PNG and JPEG files
            for filename in os.listdir(upload_dir):
                if filename.lower().endswith(('png', 'jpg', 'jpeg')):
                    file_path = os.path.join(upload_dir, filename)
                    self.wfile.write(f'<p><img src="/{filename}" alt="{filename}" /></p>'.encode())

            self.wfile.write(b'''
                    </div>
                    <h2>Download Files</h2>
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
