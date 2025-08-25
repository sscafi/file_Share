# Docker Production Deployment Guide

## 📁 Project Structure
```
enhanced-file-sharing/
├── main.py                 # Your FastAPI application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker container configuration
├── docker-compose.yml     # Multi-container orchestration
├── .dockerignore          # Files to exclude from container
├── nginx.conf             # Reverse proxy configuration
└── uploads/               # File storage (mounted volume)
```

## 🐳 Dockerfile Explained

```dockerfile
# Use Python 3.11 slim image (smaller, more secure)
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory and set permissions
RUN mkdir -p uploads && chmod 755 uploads

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8010

# Health check to ensure container is running properly
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8010/ || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "4"]
```

## 🚀 Docker Compose for Production

```yaml
version: '3.8'

services:
  # Your FastAPI application
  file-sharing-app:
    build: .
    container_name: file-sharing-service
    restart: unless-stopped
    ports:
      - "8010:8010"
    volumes:
      # Persist uploads outside container
      - ./uploads:/app/uploads
      # Mount logs for monitoring
      - ./logs:/app/logs
    environment:
      - ENVIRONMENT=production
      - MAX_FILE_SIZE=104857600  # 100MB
      - MAX_FILES_PER_REQUEST=100
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8010/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - file-sharing-network

  # Nginx reverse proxy (recommended for production)
  nginx:
    image: nginx:alpine
    container_name: file-sharing-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"  # For HTTPS
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./uploads:/var/www/uploads:ro  # Serve static files directly
      # - ./ssl:/etc/nginx/ssl:ro  # SSL certificates
    depends_on:
      - file-sharing-app
    networks:
      - file-sharing-network

  # Redis for caching (optional, for high-traffic sites)
  redis:
    image: redis:alpine
    container_name: file-sharing-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - file-sharing-network

  # PostgreSQL database (if you add user management)
  # postgres:
  #   image: postgres:15-alpine
  #   container_name: file-sharing-db
  #   restart: unless-stopped
  #   environment:
  #     POSTGRES_DB: filesharing
  #     POSTGRES_USER: app
  #     POSTGRES_PASSWORD: secure_password
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  #   networks:
  #     - file-sharing-network

networks:
  file-sharing-network:
    driver: bridge

volumes:
  redis_data:
  # postgres_data:
```

## 🌐 Nginx Configuration

```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server file-sharing-app:8010;
    }

    # Rate limiting to prevent abuse
    limit_req_zone $binary_remote_addr zone=upload:10m rate=10r/m;

    server {
        listen 80;
        server_name your-domain.com;
        
        # Increase max upload size
        client_max_body_size 1000M;
        
        # Serve static files directly (faster)
        location /static/ {
            alias /var/www/uploads/;
            expires 7d;
            add_header Cache-Control "public, immutable";
        }
        
        # Rate limit uploads
        location /upload {
            limit_req zone=upload burst=5 nodelay;
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Increase timeouts for large uploads
            proxy_connect_timeout 300s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }
        
        # All other requests
        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## 🔧 Requirements.txt

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pillow==10.0.1
aiofiles==23.2.0
python-multipart==0.0.6
redis==5.0.1
psycopg2-binary==2.9.7
```

## 🚀 Deployment Commands

### 1. Build and Start
```bash
# Build the Docker image
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f file-sharing-app
```

### 2. Scale for High Traffic
```bash
# Run 4 instances of your app
docker-compose up -d --scale file-sharing-app=4

# Check running containers
docker-compose ps
```

### 3. Updates and Maintenance
```bash
# Update your code and rebuild
git pull
docker-compose build --no-cache
docker-compose up -d

# View resource usage
docker stats

# Backup uploads
docker run --rm -v $(pwd)/uploads:/backup alpine tar czf /backup/uploads_backup.tar.gz /backup
```

## 🔒 Security Best Practices

### 1. **Non-root User**: Container runs as non-root user
### 2. **Resource Limits**: Prevent container from consuming all server resources
### 3. **Health Checks**: Monitor container health
### 4. **Volume Mounts**: Data persists outside container
### 5. **Network Isolation**: Containers communicate through private network

## 📊 Production Benefits

### **Performance**
- **Nginx**: Serves static files directly (10x faster)
- **Multiple Workers**: Handle more concurrent requests
- **Caching**: Redis for frequently accessed data

### **Reliability**
- **Auto-restart**: Containers restart automatically on failure
- **Health Checks**: Automatic container replacement if unhealthy
- **Load Balancing**: Traffic distributed across mul
