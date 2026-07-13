# Camara web en el VPS (HTTPS obligatorio)

Chrome, Edge y Firefox **bloquean la camara** si abres el panel por **HTTP** con una IP publica:

```text
http://104.238.215.26   ❌ camara bloqueada
https://104.238.215.26  ✅ camara permitida (con certificado)
http://127.0.0.1:8000   ✅ solo en tu PC local
```

Por eso aparece **"Error al iniciar camara"** sin mas detalle.

## Solucion rapida en el VPS (certificado autofirmado)

Conectate al VPS:

```bash
ssh root@104.238.215.26
```

### 1. Instalar nginx (si no lo tienes)

```bash
apt update && apt install -y nginx openssl
```

### 2. Crear certificado SSL (valido 1 ano)

```bash
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/ia-facial.key \
  -out /etc/nginx/ssl/ia-facial.crt \
  -subj "/CN=104.238.215.26"
```

### 3. Configurar nginx

```bash
cat > /etc/nginx/sites-available/ia-facial <<'EOF'
server {
    listen 80;
    server_name 104.238.215.26;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name 104.238.215.26;

    ssl_certificate     /etc/nginx/ssl/ia-facial.crt;
    ssl_certificate_key /etc/nginx/ssl/ia-facial.key;

    root /root/ia_facial/frontend;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 25m;
        proxy_read_timeout 600s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/ia-facial /etc/nginx/sites-enabled/ia-facial
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

Si nginx responde **403 Forbidden**, da permiso de lectura al frontend:

```bash
chmod 755 /root /root/ia_facial
chmod -R 755 /root/ia_facial/frontend
```

### 4. Abrir puertos (si el firewall esta activo)

```bash
ufw allow 80/tcp
ufw allow 443/tcp
```

### 5. Usar HTTPS en el navegador

Abre:

```text
https://104.238.215.26
```

Chrome mostrara **"La conexion no es privada"** (certificado autofirmado). Pulsa **Avanzado → Continuar** (una sola vez).

Luego en **Configuracion → Conexion al servidor** pon:

```text
https://104.238.215.26
```

Guarda y prueba. Ahora **Iniciar camara** debe funcionar.

## Solucion definitiva (dominio + Let's Encrypt)

Si tienes un dominio (ej. `iafacial.tudominio.com`):

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d iafacial.tudominio.com
```

Actualiza la URL del API a `https://iafacial.tudominio.com`.

## Comprobar

1. La barra del navegador debe decir **https://** (no "No es seguro" por HTTP).
2. En Escanear, pulsa **Iniciar camara** y acepta el permiso.
3. Si falla, revisa el mensaje rojo debajo del titulo (ahora explica la causa).

## Nota sobre git pull

Haz pull desde la raiz del repo:

```bash
cd ~/ia_facial && git pull
```

Si aun ves el campo **API** arriba a la derecha, el navegador tiene cache vieja: **Ctrl+Shift+R**.
