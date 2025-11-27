server {
    listen 80;
    server_name airankingx.com www.airankingx.com localhost;
    
    # Root directory for static files
    root /var/www/airankingx.com;
    index index.html;
    
    # Log files with debug level
    access_log /var/log/nginx/airankingx.com.access.log;
    error_log /var/log/nginx/airankingx.com.error.log debug;
    
    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-XSS-Protection "1; mode=block";
    
    # Global cache control for all responses
    add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
    add_header Pragma "no-cache";
    add_header Expires "0";
    
    # Static files handling with exemption from the global no-cache
    location ~* \.(css|js|jpg|jpeg|png|gif|ico)$ {
        expires 1d;
        add_header Cache-Control "public, max-age=86400";
        try_files $uri =404;
    }
    
    # Data files - disable cache
    location ~* \.(json|csv|xml)$ {
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
        add_header Pragma "no-cache";
        add_header Expires "0";
        try_files $uri =404;
    }

    # HTML files - disable cache
    location ~* \.html$ {
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
        add_header Pragma "no-cache";
        add_header Expires "0";
        try_files $uri $uri/ =404;
    }
    
    # Proxy requests to Python server - only /update_leaderboard is used
    location /update_leaderboard {
        proxy_pass http://localhost:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Increased timeout settings
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        
        # Disable cache
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }
    
    # Main location block
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Handle 404 errors
    error_page 404 /404.html;
    location = /404.html {
        root /var/www/airankingx.com;
        internal;
    }
    
    # Handle 50x errors
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /var/www/airankingx.com;
        internal;
    }
}
