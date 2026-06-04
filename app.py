import os
import json
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import anthropic
from datetime import datetime

app = Flask(__name__)

# ──────────────────────────────────────────────
#  CONFIGURACIÓN DEL RESTAURANTE
#  El dueño edita solo este bloque
# ──────────────────────────────────────────────
RESTAURANT_CONFIG = {
    "nombre": os.getenv("RESTAURANT_NAME", "Restaurante La Hacienda"),
    "telefono": os.getenv("RESTAURANT_PHONE", "+52 844 123 4567"),
    "horarios": os.getenv("RESTAURANT_HOURS", "Lunes a Sábado: 1pm - 11pm | Domingo: 12pm - 9pm"),
    "direccion": os.getenv("RESTAURANT_ADDRESS", "Blvd. Venustiano Carranza 2400, Saltillo, Coahuila"),
    "google_maps": os.getenv("RESTAURANT_MAPS_URL", "https://maps.app.goo.gl/ejemplo"),
    "capacidad_max": int(os.getenv("RESTAURANT_MAX_CAPACITY", "8")),  # personas max por reserva
    "menu": os.getenv("RESTAURANT_MENU", """
🍽️ *ENTRADAS*
• Guacamole con totopos — $85
• Sopa de lima — $75
• Flautas de pollo (3 pzas) — $90

🥩 *PLATOS FUERTES*
• Arrachera 300g + guarnición — $280
• Pollo en mole negro — $185
• Camarones al ajillo — $230
• Enchiladas verdes — $145
• Chile relleno — $155

🌮 *TACOS (orden de 3)*
• Tacos de birria — $120
• Tacos de pastor — $95
• Tacos de arrachera — $130

🥤 *BEBIDAS*
• Agua fresca — $40
• Refresco — $35
• Cerveza nacional — $55
• Michelada — $75
• Margarita — $110

🍮 *POSTRES*
• Flan napolitano — $65
• Pastel de tres leches — $70
    """),
    "pedidos_activos": os.getenv("PEDIDOS_ENABLED", "true").lower() == "true",
    "reservas_activas": os.getenv("RESERVAS_ENABLED", "true").lower() == "true",
    "whatsapp_destino": os.getenv("ORDERS_WHATSAPP", ""),  # número donde llegan pedidos/reservas
}

# ──────────────────────────────────────────────
#  CLIENTES DE API
# ──────────────────────────────────────────────
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# Memoria de conversaciones (en producción usar Redis)
conversation_history = {}

# ──────────────────────────────────────────────
#  SYSTEM PROMPT DEL AGENTE
# ──────────────────────────────────────────────
def get_system_prompt():
    config = RESTAURANT_CONFIG
    ahora = datetime.now().strftime("%A %d de %B, %Y — %H:%M hrs")
    
    return f"""Eres el asistente virtual de WhatsApp de *{config['nombre']}*.
Tu trabajo es atender a los clientes de forma amable, rápida y profesional.

📅 Fecha y hora actual: {ahora}

━━━━━━━━━━━━━━━━━━
🏠 INFORMACIÓN DEL RESTAURANTE
━━━━━━━━━━━━━━━━━━
• Nombre: {config['nombre']}
• Teléfono: {config['telefono']}
• Dirección: {config['direccion']}
• Horarios: {config['horarios']}
• Link Maps: {config['google_maps']}

━━━━━━━━━━━━━━━━━━
🍽️ MENÚ COMPLETO
━━━━━━━━━━━━━━━━━━
{config['menu']}

━━━━━━━━━━━━━━━━━━
📋 TUS CAPACIDADES
━━━━━━━━━━━━━━━━━━

1. **MENÚ**: Cuando pidan el menú, muéstralo completo y bien formateado.

2. **RESERVACIONES** ({"✅ activas" if config['reservas_activas'] else "❌ no disponibles"}):
   - Pide: nombre completo, fecha, hora, número de personas (máx {config['capacidad_max']})
   - Confirma la reservación con todos los datos
   - Formato de confirmación: incluye emoji ✅ y todos los detalles
   - Máximo {config['capacidad_max']} personas por reservación

3. **HORARIOS**: Informa claramente los horarios de operación.

4. **UBICACIÓN**: Comparte la dirección y el link de Google Maps.

5. **PEDIDOS PARA LLEVAR** ({"✅ activos" if config['pedidos_activos'] else "❌ no disponibles"}):
   - Ayuda a armar el pedido
   - Calcula el total
   - Pide nombre y hora estimada de recolección
   - Confirma el pedido con todos los detalles y total

━━━━━━━━━━━━━━━━━━
📝 REGLAS IMPORTANTES
━━━━━━━━━━━━━━━━━━
- Responde SIEMPRE en español
- Sé cordial pero conciso (WhatsApp, no ensayo)
- Usa emojis con moderación para hacer el texto más visual
- Si te preguntan algo que no sabes, di "Te comunico con el equipo 😊"
- Cuando confirmes una reserva o pedido, añade: "✅ Confirmado. Te esperamos!"
- No inventes precios ni platillos que no están en el menú
- Si el cliente dice "hola", "buenas", etc., saluda y pregunta en qué le puedes ayudar
- Formato WhatsApp: usa *negrita* y _cursiva_ cuando sea útil
"""

# ──────────────────────────────────────────────
#  WEBHOOK PRINCIPAL
# ──────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", "")
    
    if not incoming_msg:
        return Response(str(MessagingResponse()), mimetype="text/xml")
    
    # Obtener o iniciar historial del cliente
    if from_number not in conversation_history:
        conversation_history[from_number] = []
    
    history = conversation_history[from_number]
    
    # Añadir mensaje del usuario
    history.append({"role": "user", "content": incoming_msg})
    
    # Limitar historial a últimos 20 mensajes (evitar tokens excesivos)
    if len(history) > 20:
        history = history[-20:]
        conversation_history[from_number] = history
    
    # Llamar a Claude
    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",  # rápido y barato para WhatsApp
            max_tokens=600,
            system=get_system_prompt(),
            messages=history
        )
        
        bot_reply = response.content[0].text
        
    except Exception as e:
        bot_reply = "¡Hola! En este momento estamos teniendo problemas técnicos. Por favor llámanos al " + RESTAURANT_CONFIG["telefono"]
        print(f"Error Claude API: {e}")
    
    # Guardar respuesta en historial
    history.append({"role": "assistant", "content": bot_reply})
    
    # Notificar al restaurante si hay reserva o pedido confirmado
    keywords_notify = ["✅ confirmado", "reservación confirmada", "pedido confirmado", "te esperamos"]
    if any(kw in bot_reply.lower() for kw in keywords_notify):
        notify_restaurant(from_number, incoming_msg, bot_reply)
    
    # Responder via Twilio
    twilio_response = MessagingResponse()
    twilio_response.message(bot_reply)
    
    return Response(str(twilio_response), mimetype="text/xml")


# ──────────────────────────────────────────────
#  NOTIFICACIÓN AL RESTAURANTE
# ──────────────────────────────────────────────
def notify_restaurant(from_number, customer_msg, bot_reply):
    """Envía notificación al número del restaurante cuando hay reserva/pedido"""
    destino = RESTAURANT_CONFIG.get("whatsapp_destino")
    if not destino:
        return
    
    try:
        notification = (
            f"🔔 *NUEVA ACCIÓN EN BOT*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👤 Cliente: {from_number}\n"
            f"💬 Solicitó: {customer_msg[:200]}\n\n"
            f"🤖 Bot respondió:\n{bot_reply[:400]}"
        )
        twilio_client.messages.create(
            body=notification,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{destino}"
        )
    except Exception as e:
        print(f"Error notificando restaurante: {e}")


# ──────────────────────────────────────────────
#  RUTAS AUXILIARES
# ──────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "restaurant": RESTAURANT_CONFIG["nombre"]}, 200


@app.route("/reset/<phone>", methods=["GET"])
def reset_conversation(phone):
    """Resetea conversación de un número (para testing)"""
    key = f"whatsapp:+{phone}"
    if key in conversation_history:
        del conversation_history[key]
        return {"status": "reset", "phone": key}, 200
    return {"status": "not found"}, 404


@app.route("/", methods=["GET"])
def index():
    return {
        "bot": RESTAURANT_CONFIG["nombre"],
        "status": "🟢 Online",
        "features": {
            "menu": True,
            "reservaciones": RESTAURANT_CONFIG["reservas_activas"],
            "pedidos": RESTAURANT_CONFIG["pedidos_activos"],
            "horarios": True,
            "ubicacion": True
        }
    }, 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
