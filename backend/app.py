import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
# CORS permite que el frontend (Vue) se comunique con este backend
CORS(app)

# Configuración de la base de datos PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/gastogenie')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configuración de Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY no encontrada en las variables de entorno.")

# Modelo SQLAlchemy
class Gasto(db.Model):
    __tablename__ = 'gastos'
    id = db.Column(db.Integer, primary_key=True)
    monto = db.Column(db.Float, nullable=False)
    comercio = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    moneda = db.Column(db.String(10), nullable=False, default="EUR")
    texto_original = db.Column(db.Text, nullable=True)

    def __init__(self, monto, comercio, fecha, categoria, moneda="EUR", texto_original=None):
        self.monto = monto
        self.comercio = comercio
        self.fecha = fecha
        self.categoria = categoria
        self.moneda = moneda
        self.texto_original = texto_original

    def to_dict(self):
        return {
            "id": self.id,
            "monto": self.monto,
            "comercio": self.comercio,
            "fecha": self.fecha.strftime('%Y-%m-%d') if self.fecha else None,
            "categoria": self.categoria,
            "moneda": self.moneda,
            "texto_original": self.texto_original
        }

# Inicializar Base de Datos (en un caso de uso real se usaría Flask-Migrate)
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Warning: Could not connect to the database. {e}")

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"mensaje": "¡Backend de Flask funcionando a la perfección!"})

@app.route('/api/procesar', methods=['POST'])
def procesar_gasto():
    data = request.json
    if not data or 'texto' not in data:
        return jsonify({"error": "No se proporcionó ningún texto."}), 400
    
    texto = data['texto']
    
    if not GEMINI_API_KEY:
         return jsonify({"error": "La API Key de Gemini no está configurada en el servidor."}), 500

    try:
        # Prompt estructurado para Gemini
        prompt = f"""
        Eres un asistente inteligente para la aplicación "GastoGenie" (Smart Expense Tracker).
        Extrae la siguiente información del texto proporcionado por el usuario y devuélvela EXCLUSIVAMENTE como un objeto JSON válido, sin bloques de código Markdown ni texto adicional. Solo imprime las llaves {{ y }}.
        
        Las claves requeridas en el JSON son:
        - "monto": (number) número flotante extraído (ej. 35.0).
        - "comercio": (string) el nombre del lugar o comercio (ej. "Ginos"). Si no se menciona o deduce claramente, usa "Desconocido".
        - "fecha": (string) la fecha inferida en formato "YYYY-MM-DD". IMPORTANTE: Hoy es {datetime.now().strftime('%Y-%m-%d')}. "Ayer" es {(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')}.
        - "categoria": (string) la categoría del gasto (ej. "Comida", "Transporte", "Ocio", "Hogar", "Otros").
        - "moneda": (string) la moneda (ej. "EUR", "USD"). Si no se especifica, asume "EUR".
        
        Texto del usuario: "{texto}"
        """
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Limpieza de markdown para seguridad
        if content.startswith('```json'):
            content = content[7:-3].strip()
        elif content.startswith('```'):
            content = content[3:-3].strip()
            
        json_data = json.loads(content)
        return jsonify(json_data), 200

    except Exception as e:
        print(f"Error procesando con Gemini: {e}")
        return jsonify({"error": "Error interno al procesar el texto con la Inteligencia Artificial.", "detalle": str(e)}), 500

@app.route('/api/gastos', methods=['POST'])
def crear_gasto():
    data = request.json
    try:
        nuevo_gasto = Gasto(
            monto=float(data.get('monto')),
            comercio=data.get('comercio'),
            fecha=datetime.strptime(data.get('fecha'), '%Y-%m-%d').date(),
            categoria=data.get('categoria'),
            moneda=data.get('moneda', 'EUR'),
            texto_original=data.get('texto_original', '')
        )
        db.session.add(nuevo_gasto)
        db.session.commit()
        return jsonify(nuevo_gasto.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Error al guardar el gasto en la base de datos.", "detalle": str(e)}), 400

@app.route('/api/gastos', methods=['GET'])
def obtener_gastos():
    try:
        gastos = Gasto.query.order_by(Gasto.fecha.desc(), Gasto.id.desc()).all()
        return jsonify([g.to_dict() for g in gastos]), 200
    except Exception as e:
        return jsonify({"error": "Error al obtener los gastos.", "detalle": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)