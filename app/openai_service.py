import os

import openai
import json
import re

# Configura tu clave API de OpenAI
openai.api_key = os.getenv('API_KEY_OPENAI')  # Reemplaza con tu clave real


def parse_suggestions_to_json(suggestions_text):
    """
    Convierte el texto estructurado de OpenAI en un JSON válido.
    """
    suggestions = []
    current_suggestion = {}

    # Dividir la respuesta en líneas
    lines = suggestions_text.split("\n")

    for line in lines:
        if line.startswith("Problema:"):
            current_suggestion["problema"] = line.replace("Problema:", "").strip()
        elif line.startswith("Solución:"):
            current_suggestion["solucion"] = line.replace("Solución:", "").strip()
        elif line.startswith("Ejemplo de Código:"):
            current_suggestion["ejemplo_codigo"] = line.replace("Ejemplo de Código:", "").strip()
            suggestions.append(current_suggestion)
            current_suggestion = {}  # Reiniciar para la siguiente violación

    return {"violations": suggestions}


def generate_suggestions(violations):
    try:
        # Convertir el objeto violations a una cadena JSON
        violations_str = json.dumps(violations, ensure_ascii=False, indent=2)

        # Crear el prompt simplificado
        prompt = (
            "Aquí tienes un JSON con problemas de accesibilidad encontrados (clave 'violations'). "
            "Proporciona una sugerencia estructurada en español para cada violación en el siguiente formato:\n"
            "Problema: [Descripción del problema]\n"
            "Solución: [Descripción de la solución]\n"
            "Ejemplo de Código: [Ejemplo de código en una sola línea si es necesario]\n\n"
            "No devuelvas JSON ni bloques de código, solo el texto estructurado en el formato anterior."
        )

        # Llamar a la API de OpenAI para obtener sugerencias en formato de texto
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente de accesibilidad web."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2048,
            temperature=0.7
        )

        # Obtener la respuesta de OpenAI como texto
        suggestions_text = response['choices'][0]['message']['content'].strip()

        # Convertir la respuesta en un JSON válido
        suggestions_json = parse_suggestions_to_json(suggestions_text)

        return suggestions_json

    except Exception as e:
        print(f"Error al generar sugerencias con OpenAI: {e}")
        return {"error": str(e)}