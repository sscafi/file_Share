from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import aiofiles
import zipfile
import io
import os
from pathlib import Path
from typing import List
import mimetypes
from PIL import Image
import logging
from contextlib import asynccontextmanager
import tempfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_DIR = Path("uploads")
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB per file
MAX_FILES_PER_REQUEST = 100
SUPPORTED_IMAGE_FORMATS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
SUPPORTED_FORMATS = SUPPORTED_IMAGE_FORMATS | {'.pdf', '.txt', '.docx', '.xlsx', '.zip', '.mp4', '.mp3'}

# Ensure upload directory exists
UPLOAD_DIR.mkdir(exist_ok=True)

class FileProcessor:
    """Handles file processing operations"""
    
    @staticmethod
    async def convert_image(file_path: Path, target_format: str = 'JPEG') -> Path:
        """Convert image to target format asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, FileProcessor._convert_image_sync, file_path, target_format)
        except Exception as e:
            logger.error(f"Error converting {file_path}: {e}")
            return file_path
    
    @staticmethod
    def _convert_image_sync(file_path: Path, target_format: str) -> Path:
        """Synchronous image conversion"""
        if not file_path.suffix.lower() in SUPPORTED_IMAGE_FORMATS:
            return file_path
            
        target_path = file_path.with_suffix('.jpg' if target_format == 'JPEG' else '.png')
        
        try:
            with Image.open(file_path) as img:
                # Convert RGBA to RGB for JPEG
                if target_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(target_path, target_format)
                
            # Remove original if conversion successful and formats differ
            if target_path != file_path:
                file_path.unlink()
                logger.info(f"Converted {file_path.name} to {target_path.name}")
                
            return target_path
        except Exception as e:
            logger.error(f"Image conversion failed for {file_path}: {e}")
            return file_path

    @staticmethod
    def validate_file(filename: str, file_size: int) -> tuple[bool, str]:
        """Validate file based on extension and size"""
        file_path = Path(filename)
        
        if file_size > MAX_FILE_SIZE:
            return False, f"File size {file_size} exceeds maximum allowed size {MAX_FILE_SIZE}"
        
        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
            return False, f"File type {file_path.suffix} not supported"
        
        return True, "Valid"

class FileManager:
    """Manages file operations"""
    
    @staticmethod
    async def save_file(file: UploadFile) -> tuple[bool, str, Path]:
        """Save uploaded file asynchronously"""
        try:
            # Validate file
            is_valid, message = FileProcessor.validate_file(file.filename, file.size or 0)
            if not is_valid:
                return False, message, None
            
            # Create safe filename
            safe_filename = FileManager._create_safe_filename(file.filename)
            file_path = UPLOAD_DIR / safe_filename
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            logger.info(f"Saved file: {safe_filename}")
            return True, "File saved successfully", file_path
            
        except Exception as e:
            logger.error(f"Error saving file {file.filename}: {e}")
            return False, f"Error saving file: {str(e)}", None
    
    @staticmethod
    def _create_safe_filename(filename: str) -> str:
        """Create a safe filename avoiding conflicts"""
        path = Path(filename)
        safe_name = "".join(c for c in path.stem if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name[:50]  # Limit length
        
        counter = 1
        new_path = UPLOAD_DIR / f"{safe_name}{path.suffix}"
        
        while new_path.exists():
            new_path = UPLOAD_DIR / f"{safe_name}_{counter}{path.suffix}"
            counter += 1
            
        return new_path.name
    
    @staticmethod
    def get_files_by_type() -> dict:
        """Organize files by type"""
        files_by_type = {
            'images': [],
            'documents': [],
            'media': [],
            'other': []
        }
        
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                if suffix in SUPPORTED_IMAGE_FORMATS:
                    files_by_type['images'].append(file_path.name)
                elif suffix in {'.pdf', '.txt', '.docx', '.xlsx'}:
                    files_by_type['documents'].append(file_path.name)
                elif suffix in {'.mp4', '.mp3'}:
                    files_by_type['media'].append(file_path.name)
                else:
                    files_by_type['other'].append(file_path.name)
        
        return files_by_type

# FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting File Sharing Service")
    yield
    logger.info("Shutting down File Sharing Service")

app = FastAPI(
    title="Enhanced File Sharing Service",
    description="A robust file sharing service with support for multiple formats and batch uploads",
    version="2.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_upload_page():
    """Serve the main upload page"""
    files_by_type = FileManager.get_files_by_type()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Enhanced File Sharing Service</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }}
            h1 {{
                text-align: center;
                color: #333;
                margin-bottom: 30px;
                font-size: 2.5em;
            }}
            .upload-area {{
                border: 3px dashed #667eea;
                border-radius: 15px;
                padding: 40px;
                text-align: center;
                margin-bottom: 30px;
                background: #f8f9ff;
                transition: all 0.3s ease;
            }}
            .upload-area:hover {{
                border-color: #764ba2;
                background: #f0f2ff;
            }}
            .file-input {{
                display: none;
            }}
            .upload-btn {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 30px;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                font-size: 16px;
                transition: transform 0.3s ease;
            }}
            .upload-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
            }}
            .file-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }}
            .file-section {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                border-left: 5px solid #667eea;
            }}
            .file-section h3 {{
                margin-top: 0;
                color: #333;
            }}
            .file-item {{
                padding: 8px;
                margin: 5px 0;
                background: white;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .progress-bar {{
                width: 100%;
                height: 20px;
                background: #f0f0f0;
                border-radius: 10px;
                overflow: hidden;
                margin: 20px 0;
                display: none;
            }}
            .progress-fill {{
                height: 100%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                width: 0%;
                transition: width 0.3s ease;
            }}
            .status {{
                margin: 20px 0;
                padding: 15px;
                border-radius: 5px;
                display: none;
            }}
            .status.success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            .status.error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📁 Enhanced File Sharing Service</h1>
            
            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <h3>📤 Drop files here or click to upload</h3>
                <p>Supports images, documents, media files • Max 100 files • 100MB per file</p>
                <button class="upload-btn" type="button">Choose Files</button>
                <input type="file" id="fileInput" class="file-input" multiple accept=".png,.jpg,.jpeg,.gif,.bmp,.tiff,.webp,.pdf,.txt,.docx,.xlsx,.zip,.mp4,.mp3">
            </div>
            
            <div class="progress-bar" id="progressBar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            
            <div class="status" id="status"></div>
            
            <button class="upload-btn" onclick="uploadFiles()" id="uploadButton" style="display: none;">Upload Selected Files</button>
            
            <div class="file-grid">
                <div class="file-section">
                    <h3>🖼️ Images ({len(files_by_type['images'])})</h3>
                    {"".join([f'<div class="file-item"><a href="/static/{file}" target="_blank">{file}</a></div>' for file in files_by_type['images']])}
                </div>
                
                <div class="file-section">
                    <h3>📄 Documents ({len(files_by_type['documents'])})</h3>
                    {"".join([f'<div class="file-item"><a href="/static/{file}" target="_blank">{file}</a></div>' for file in files_by_type['documents']])}
                </div>
                
                <div class="file-section">
                    <h3>🎵 Media ({len(files_by_type['media'])})</h3>
                    {"".join([f'<div class="file-item"><a href="/static/{file}" target="_blank">{file}</a></div>' for file in files_by_type['media']])}
                </div>
                
                <div class="file-section">
                    <h3>📦 Other ({len(files_by_type['other'])})</h3>
                    {"".join([f'<div class="file-item"><a href="/static/{file}" target="_blank">{file}</a></div>' for file in files_by_type['other']])}
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/download" class="upload-btn">📥 Download All Files (ZIP)</a>
            </div>
        </div>
        
        <script>
            let selectedFiles = [];
            
            document.getElementById('fileInput').addEventListener('change', function(e) {{
                selectedFiles = Array.from(e.target.files);
                updateFileDisplay();
            }});
            
            function updateFileDisplay() {{
                const button = document.getElementById('uploadButton');
                if (selectedFiles.length > 0) {{
                    button.style.display = 'inline-block';
                    button.textContent = `Upload ${{selectedFiles.length}} file(s)`;
                }} else {{
                    button.style.display = 'none';
                }}
            }}
            
            async function uploadFiles() {{
                if (selectedFiles.length === 0) return;
                
                const progressBar = document.getElementById('progressBar');
                const progressFill = document.getElementById('progressFill');
                const status = document.getElementById('status');
                const button = document.getElementById('uploadButton');
                
                progressBar.style.display = 'block';
                button.disabled = true;
                
                const formData = new FormData();
                selectedFiles.forEach(file => {{
                    formData.append('files', file);
                }});
                
                try {{
                    const response = await fetch('/upload', {{
                        method: 'POST',
                        body: formData
                    }});
                    
                    if (response.ok) {{
                        const result = await response.json();
                        progressFill.style.width = '100%';
                        status.className = 'status success';
                        status.style.display = 'block';
                        status.innerHTML = `✅ Successfully uploaded ${{result.successful}} files. ${{result.failed > 0 ? `Failed: ${{result.failed}}` : ''}}`;
                        
                        setTimeout(() => {{
                            location.reload();
                        }}, 2000);
                    }} else {{
                        throw new Error('Upload failed');
                    }}
                }} catch (error) {{
                    status.className = 'status error';
                    status.style.display = 'block';
                    status.innerHTML = `❌ Upload failed: ${{error.message}}`;
                }} finally {{
                    button.disabled = false;
                    setTimeout(() => {{
                        progressBar.style.display = 'none';
                        progressFill.style.width = '0%';
                    }}, 3000);
                }}
            }}
            
            // Drag and drop functionality
            const uploadArea = document.querySelector('.upload-area');
            
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {{
                uploadArea.addEventListener(eventName, preventDefaults, false);
            }});
            
            function preventDefaults(e) {{
                e.preventDefault();
                e.stopPropagation();
            }}
            
            uploadArea.addEventListener('drop', function(e) {{
                const files = Array.from(e.dataTransfer.files);
                selectedFiles = files;
                updateFileDisplay();
            }});
        </script>
    </body>
    </html>
    """
    return html_content

@app.post("/upload")
async def upload_files(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    """Handle multiple file uploads with validation and processing"""
    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum {MAX_FILES_PER_REQUEST} files allowed per request"
        )
    
    results = {"successful": 0, "failed": 0, "errors": []}
    
    # Process files concurrently
    tasks = []
    for file in files:
        if file.filename:
            tasks.append(FileManager.save_file(file))
    
    # Wait for all uploads to complete
    upload_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results and schedule background tasks
    for i, result in enumerate(upload_results):
        if isinstance(result, Exception):
            results["failed"] += 1
            results["errors"].append(f"File {files[i].filename}: {str(result)}")
        else:
            success, message, file_path = result
            if success:
                results["successful"] += 1
                # Schedule image conversion in background
                if file_path and file_path.suffix.lower() == '.png':
                    background_tasks.add_task(FileProcessor.convert_image, file_path)
            else:
                results["failed"] += 1
                results["errors"].append(f"File {files[i].filename}: {message}")
    
    return results

@app.get("/download")
async def download_all_files():
    """Create and serve a ZIP file of all uploads"""
    def create_zip():
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in UPLOAD_DIR.iterdir():
                if file_path.is_file():
                    zip_file.write(file_path, file_path.name)
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    # Create ZIP in thread to avoid blocking
    loop = asyncio.get_event_loop()
    zip_data = await loop.run_in_executor(None, create_zip)
    
    return StreamingResponse(
        io.BytesIO(zip_data),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=uploaded_files.zip"}
    )

@app.get("/files")
async def list_files():
    """API endpoint to list all files by category"""
    return FileManager.get_files_by_type()

@app.delete("/files/{filename}")
async def delete_file(filename: str):
    """Delete a specific file"""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        file_path.unlink()
        return {"message": f"File {filename} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8010,
        reload=True,
        log_level="info"
    )
