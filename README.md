# Multi-File Upload and Download HTTP Server

This project implements a simple HTTP server in Python that allows users to upload multiple files and download them as a ZIP file. The server serves files from a designated upload directory within the user's OneDrive folder.

## Features

- **Multi-File Upload**: Users can select and upload multiple files at once.
- **Download Functionality**: Users can download all uploaded files as a ZIP file.
- **User -Friendly HTML Interface**: A simple web interface for uploading and downloading files.

## Requirements

To run this project, you need to have Python installed on your machine. Additionally, you will need the following Python packages:

- `http.server`
- `socketserver`
- `os`
- `zipfile`
- `io`

These libraries are included in the Python standard library, so no additional installation is required.

## Usage

1. Clone or download this repository to your local machine.
2. Navigate to the directory where the script is located.
3. Run the script using Python:

   ```bash
   python file_share.py

## serving port 8010
