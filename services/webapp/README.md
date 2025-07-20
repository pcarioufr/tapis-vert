# Webapp - Flask Applications

This directory contains the split Flask applications for Tapis Vert, with shared templates and static assets.

## 🏗️ **Architecture Overview**

```
webapp/
├── static/                    # 🎨 Shared static assets
│   ├── commons/              # Shared fonts, libs, styles
│   │   ├── fonts/           # Font files
│   │   ├── libs/            # JavaScript libraries
│   │   ├── styles/          # Common CSS components
│   │   └── layout.css       # Main layout CSS
│   ├── public/              # Public app specific assets
│   │   └── styles/          # Room/game specific CSS
│   └── admin/               # Admin app specific assets
│       └── styles/          # Admin interface CSS
├── templates/                # 🎯 Shared template system  
│   ├── commons/             # Shared template components
│   │   ├── layout.jinja     # Main layout template
│   │   ├── elements.jinja   # UI components
│   │   ├── buttons.jinja    # Button components
│   │   └── ...              # Other shared components
│   ├── public/              # Public app templates
│   │   └── room/            # Game room templates
│   └── admin/               # Admin app templates
│       └── admin/           # Admin interface templates
├── flask-public/            # 🌐 Public-facing Flask app
│   ├── app/                 # Application code
│   ├── .build/              # Docker build context
│   └── wsgi.py              # WSGI entry point
├── flask-admin/             # 🔒 Admin-only Flask app
│   ├── app/                 # Application code 
│   ├── .build/              # Docker build context
│   └── wsgi.py              # WSGI entry point
├── libs/                    # 📚 Shared Python libraries
└── websocket/               # 🔌 WebSocket server
```

## 🎯 **Flask App Structure**

### **Public App** (`flask-public/`)
- **Purpose**: User-facing game interface
- **Access**: Public internet via nginx
- **Features**: Rooms, authentication, QR codes, game mechanics
- **Port**: 8001 (internal)
- **Templates**: Uses `public/` and `commons/` templates
- **Static Assets**: Uses `public/` and `commons/` static files

### **Admin App** (`flask-admin/`) 
- **Purpose**: Administration interface
- **Access**: Localhost only via SSH tunnel
- **Features**: User management, room management, Redis debugging
- **Port**: 8002 (internal)
- **Templates**: Uses `admin/` and `commons/` templates  
- **Static Assets**: Uses `admin/` and `commons/` static files

## 🔄 **Template System**

### **Template Organization**
```
templates/
├── commons/layout.jinja      # ← Main layout extended by all pages
├── commons/elements.jinja    # ← Shared UI components
├── public/room/_room.jinja   # ← Game room interface  
└── admin/admin/_list.jinja   # ← Admin dashboard
```

### **Template Inheritance**
```jinja
{% extends 'commons/layout.jinja' %}     <!-- All pages extend main layout -->
{% include 'commons/elements.jinja' %}  <!-- Shared components -->
{% include 'public/room/cards.jinja' %} <!-- App-specific includes -->
```

### **Static File References**
```jinja
<!-- Commons assets (shared by all apps) -->
{{ url_for('static', filename='commons/layout.css') }}
{{ url_for('static', filename='commons/libs/websocket.js') }}

<!-- App-specific assets -->
{{ url_for('static', filename='public/styles/cards.css') }}
{{ url_for('static', filename='admin/styles/list.css') }}
```

## 🔧 **Build & Deployment**

### **Development**
```bash
# Build both apps
cd services/
docker compose build flask-public flask-admin

# Run with hot-reload
docker compose up flask-public flask-admin
```

### **Production Deployment**
```bash
# Deploy code changes
cd box/
box deploy

# Restart services (shared assets auto-updated)
box ssh "cd services && docker compose restart flask-public flask-admin"
```

### **Volume Mounts**
Each Flask app gets:
- **App code**: `./flask-{app}:/flask` (read-write)
- **Shared libs**: `./libs:/opt/libs:ro` (read-only)
- **Shared static**: `./static:/flask/static:ro` (read-only)
- **Shared templates**: `./templates:/flask/templates:ro` (read-only)

## 🎨 **Adding New Assets**

### **Shared Asset** (used by both apps)
```bash
# Add to commons
echo "/* shared styles */" > static/commons/styles/new-component.css

# Include in commons/layout.jinja
<link rel="stylesheet" href="{{ url_for('static', filename='commons/styles/new-component.css') }}">
```

### **App-specific Asset**
```bash
# Add to specific app
echo "/* public only */" > static/public/styles/new-feature.css

# Include in app-specific template
<link rel="stylesheet" href="{{ url_for('static', filename='public/styles/new-feature.css') }}">
```

## 🛠️ **Benefits of This Structure**

1. **🎯 Single Source of Truth**: Shared assets in one place
2. **🔄 No Duplication**: Common styles/scripts shared between apps
3. **🎨 Easy Theming**: Update commons to change both apps
4. **📦 Clean Separation**: App-specific assets clearly organized
5. **🚀 Fast Development**: Changes apply to both apps instantly
6. **📝 Clear Organization**: Intuitive directory structure

## 🔍 **Troubleshooting**

### **Template Not Found**
- Check if template path uses correct subdirectory (`public/`, `admin/`, `commons/`)
- Verify template extends `commons/layout.jinja`

### **Static Asset 404**
- Confirm asset is in correct subdirectory
- Check `url_for('static', filename='...')` path includes subdirectory

### **Hot Reload Issues**
- Restart containers to pick up new volume mounts
- Check Docker volume mounts in `compose.yml` 