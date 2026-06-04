# 🤖 Agente WhatsApp para Restaurantes

Bot de IA para WhatsApp que atiende clientes de restaurantes automáticamente.
Construido con **Claude (Anthropic)** + **Twilio** + **Flask**.

---

## ✅ ¿Qué puede hacer el bot?

| Función | Descripción |
|--------|------------|
| 🍽️ Menú | Envía el menú completo formateado |
| 📅 Reservaciones | Toma reservas (nombre, fecha, hora, personas) |
| 🕐 Horarios | Informa horarios de atención |
| 📍 Ubicación | Comparte dirección + link Google Maps |
| 🛍️ Pedidos para llevar | Arma pedido, calcula total, confirma |
| 🔔 Notificaciones | Avisa al restaurante cuando hay reserva/pedido |

---

## 🚀 Deploy en Railway (5 minutos)

### Paso 1 — Subir a GitHub
```bash
git init
git add .
git commit -m "whatsapp bot"
git remote add origin https://github.com/TU_USUARIO/restaurant-bot.git
git push -u origin main
```

### Paso 2 — Crear proyecto en Railway
1. Ve a [railway.app](https://railway.app)
2. **New Project → Deploy from GitHub**
3. Selecciona tu repo

### Paso 3 — Agregar variables de entorno
En Railway → tu servicio → **Variables**, agrega:

```
TWILIO_ACCOUNT_SID       = ACxxxxxxxxxx  (de Twilio Console)
TWILIO_AUTH_TOKEN        = xxxxxxxxxx    (de Twilio Console)
TWILIO_WHATSAPP_NUMBER   = whatsapp:+14155238886
ANTHROPIC_API_KEY        = sk-ant-xxxxx  (de console.anthropic.com)
RESTAURANT_NAME          = Nombre del restaurante
RESTAURANT_PHONE         = +52 XXX XXX XXXX
RESTAURANT_HOURS         = Lun-Sab 1pm-11pm
RESTAURANT_ADDRESS       = Dirección completa
RESTAURANT_MAPS_URL      = https://maps.app.goo.gl/...
ORDERS_WHATSAPP          = +521XXXXXXXXXX  (tu número)
RESTAURANT_MAX_CAPACITY  = 8
```

### Paso 4 — Configurar Twilio Sandbox

1. Ve a **Twilio Console → Messaging → Try it out → WhatsApp**
2. En **Sandbox Settings → When a message comes in:**
   ```
   https://TU-APP.railway.app/webhook
   ```
3. Método: **POST**
4. Guarda

### Paso 5 — Probar
Escanea el QR de Twilio Sandbox con WhatsApp y escribe *"hola"*.

---

## ⚙️ Personalizar menú

Edita la variable `RESTAURANT_MENU` en Railway con formato WhatsApp:

```
🍽️ *ENTRADAS*
• Guacamole — $85
• Sopa de lima — $75

🥩 *PLATOS FUERTES*  
• Arrachera — $280
```

---

## 💰 Costos estimados

| Servicio | Costo |
|---------|-------|
| Railway | ~$5 USD/mes |
| Twilio (1000 mensajes) | ~$7.50 USD |
| Claude Haiku (1000 conversaciones) | ~$2 USD |
| **Total aprox.** | **~$15 USD/mes** |

---

## 🛠️ Estructura del proyecto

```
whatsapp-restaurant-bot/
├── app.py              ← Lógica principal
├── requirements.txt    ← Dependencias Python
├── Procfile            ← Comando de inicio
├── railway.toml        ← Config de Railway
├── .env.example        ← Variables de entorno (template)
└── README.md           ← Este archivo
```

---

## 📲 Flujo de conversación

```
Cliente: "hola"
Cliente: "quiero ver el menú"
  Bot: [Envía menú completo formateado]

Cliente: "quiero hacer una reservación"
  Bot: "¡Claro! ¿A qué nombre? ¿Para qué fecha y hora? ¿Cuántas personas?"

Cliente: "para mañana a las 8pm, 4 personas, nombre García"
  Bot: "✅ Confirmado. Reservación para García, 4 personas, [fecha] 8pm. ¡Te esperamos!"
  [Notificación automática al restaurante]
```

---

## 🔧 API Endpoints

| Endpoint | Método | Descripción |
Cliente: "hola"
| `/` | GET | Status del bot |
| `/webhook` | POST | Recibe mensajes de Twilio |
| `/health` | GET | Health check para Railway |
| `/reset/<phone>` | GET | Reset conversación (testing) |

---

Construido por **Sergio** • Freelance AI Agent Developer
