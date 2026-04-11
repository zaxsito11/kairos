from dotenv import load_dotenv
import os
from groq import Groq

# Cargar variables del archivo .env
load_dotenv()

# Conectar con Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Prueba simple
respuesta = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {
            "role": "user",
            "content": "Di exactamente esto: KAIROS conectado correctamente."
        }
    ]
)

print(respuesta.choices[0].message.content)