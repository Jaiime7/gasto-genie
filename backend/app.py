import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from google import genai

load_dotenv()

app = Flask(__name__)
# CORS permite que el frontend (Vue) se comunique con este backend
CORS(app)

# Configuración de la base de datos (SQLite por defecto para que funcione sin configurar PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///gastogenie.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configuración de subidas de archivos
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configuración de Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None
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
    ruta_recibo = db.Column(db.String(200), nullable=True)

    def __init__(self, monto, comercio, fecha, categoria, moneda="EUR", texto_original=None, ruta_recibo=None):
        self.monto = monto
        self.comercio = comercio
        self.fecha = fecha
        self.categoria = categoria
        self.moneda = moneda
        self.texto_original = texto_original
        self.ruta_recibo = ruta_recibo

    def to_dict(self):
        return {
            "id": self.id,
            "monto": self.monto,
            "comercio": self.comercio,
            "fecha": self.fecha.strftime('%Y-%m-%d') if self.fecha else None,
            "categoria": self.categoria,
            "moneda": self.moneda,
            "texto_original": self.texto_original,
            "ruta_recibo": self.ruta_recibo
        }

class Ingreso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monto = db.Column(db.Float, nullable=False)
    fuente = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    es_nomina = db.Column(db.Boolean, default=True)

    def __init__(self, monto, fuente, fecha, es_nomina=True):
        self.monto = monto
        self.fuente = fuente
        if isinstance(fecha, str):
            self.fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
        else:
            self.fecha = fecha
        self.es_nomina = es_nomina

class Presupuesto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(50), nullable=False)
    monto_limite = db.Column(db.Float, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    año = db.Column(db.Integer, nullable=False)

    def __init__(self, categoria, monto_limite, mes, año):
        self.categoria = categoria
        self.monto_limite = monto_limite
        self.mes = mes
        self.año = año

class GastoFijo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    pagado = db.Column(db.Boolean, default=False)

    def __init__(self, nombre, monto, categoria='Hogar', pagado=False):
        self.nombre = nombre
        self.monto = monto
        self.categoria = categoria
        self.pagado = pagado

class ObjetivoAhorro(db.Model):
    __tablename__ = 'objetivos_ahorro'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    meta_monto = db.Column(db.Float, nullable=False)
    monto_actual = db.Column(db.Float, nullable=False, default=0.0)
    fecha_limite = db.Column(db.Date, nullable=True)

    def __init__(self, nombre, meta_monto, monto_actual=0.0, fecha_limite=None):
        self.nombre = nombre
        self.meta_monto = meta_monto
        self.monto_actual = monto_actual
        if isinstance(fecha_limite, str) and fecha_limite:
            self.fecha_limite = datetime.strptime(fecha_limite, '%Y-%m-%d').date()
        else:
            self.fecha_limite = fecha_limite

    def to_dict(self):
        pct = round((self.monto_actual / self.meta_monto) * 100, 1) if self.meta_monto > 0 else 0
        return {
            "id": self.id,
            "nombre": self.nombre,
            "meta_monto": self.meta_monto,
            "monto_actual": self.monto_actual,
            "fecha_limite": self.fecha_limite.strftime('%Y-%m-%d') if self.fecha_limite else None,
            "porcentaje": min(pct, 100)
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

@app.route('/api/escanear', methods=['POST'])
def escanear_recibo():
    if not client:
        return jsonify({"error": "La API Key de Gemini no está configurada en el servidor."}), 500

    if 'recibo' not in request.files:
        return jsonify({"error": "No se proporcionó ningún recibo."}), 400

    file = request.files['recibo']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S_scan")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
        file.save(filepath)
        
        try:
            uploaded_file = client.files.upload(file=filepath)
            prompt = f"""
            Analiza este documento (puede ser una imagen o un PDF de factura o de nómina/payroll).
            Extrae la siguiente información exclusivamente en un objeto JSON válido.
            
            Si el documento es una NÓMINA o RECIBO DE SUELDO:
            - "tipo_documento": "ingreso"
            - "monto": (number) el sueldo neto cobrado.
            - "comercio": (string) el nombre de la empresa pagadora.
            - "fecha": (string) "YYYY-MM-DD".
            - "categoria": "Sueldo"
            
            Si el documento es un RECIBO DE GASTO:
            - "tipo_documento": "gasto"
            - "monto": (number) total.
            - "comercio": (string) nombre del negocio.
            - "fecha": (string) "YYYY-MM-DD".
            - "categoria": (string) categoría del gasto.
            
            IMPORTANTE: Hoy es {datetime.now().strftime('%Y-%m-%d')}.
            Deduce la moneda de forma inteligente (default "EUR").
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[uploaded_file, prompt]
            )
            content = response.text.strip()
            
            if content.startswith('```json'):
                content = content[7:-3].strip()
            elif content.startswith('```'):
                content = content[3:-3].strip()
                
            json_data = json.loads(content)
            
            # Limpiar archivo temporal de escaneo para no ensuciar la carpeta
            if os.path.exists(filepath):
                os.remove(filepath)
                
            return jsonify({"datos": json_data}), 200
        except Exception as e:
            print(f"Error procesando OCR: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"error": "Error interno al procesar el recibo con Inteligencia Artificial.", "detalle": str(e)}), 500
            
    return jsonify({"error": "Formato de archivo no permitido."}), 400

@app.route('/api/procesar', methods=['POST'])
def procesar_gasto():
    data = request.json
    if not data or 'texto' not in data:
        return jsonify({"error": "No se proporcionó ningún texto."}), 400
    
    texto = data['texto']
    
    if not client:
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
        - "moneda": (string) la moneda (ej. "EUR", "USD", "MXN"). Si no se especifica explícitamente, intenta deducirla por el contexto geográfico o el modismo del lenguaje (ej. si escribe en español de España asume "EUR", si es de México "MXN"). Si no logras deducirlo, usa "EUR" por defecto.
        
        Texto del usuario: "{texto}"
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
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
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        data = request.form
    else:
        data = request.json or {}

    ruta_recibo = None
    if 'recibo' in request.files:
        file = request.files['recibo']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            ruta_recibo = filename

    try:
        nuevo_gasto = Gasto(
            monto=float(data.get('monto', 0)),
            comercio=data.get('comercio'),
            fecha=datetime.strptime(data.get('fecha'), '%Y-%m-%d').date(),
            categoria=data.get('categoria'),
            moneda=data.get('moneda', 'EUR'),
            texto_original=data.get('texto_original', ''),
            ruta_recibo=ruta_recibo
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

@app.route('/api/gastos/<int:id>', methods=['DELETE'])
def eliminar_gasto(id):
    try:
        gasto = db.session.get(Gasto, id)
        if not gasto:
            return jsonify({"error": "Gasto no encontrado."}), 404
        
        # Eliminar el archivo físico si existe
        if gasto.ruta_recibo:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], gasto.ruta_recibo)
            if os.path.exists(filepath):
                os.remove(filepath)
                
        db.session.delete(gasto)
        db.session.commit()
        return jsonify({"mensaje": "Gasto eliminado exitosamente."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Error al eliminar el gasto.", "detalle": str(e)}), 500

@app.route('/api/gastos/<int:id>', methods=['PUT'])
def actualizar_gasto(id):
    try:
        gasto = db.session.get(Gasto, id)
        if not gasto:
            return jsonify({"error": "Gasto no encontrado."}), 404
        data = request.get_json(silent=True) or {}
        if data.get('monto'):     gasto.monto = float(data['monto'])
        if data.get('comercio'):  gasto.comercio = data['comercio']
        if data.get('fecha'):     gasto.fecha = datetime.strptime(data['fecha'], '%Y-%m-%d').date()
        if data.get('categoria'): gasto.categoria = data['categoria']
        if data.get('moneda'):    gasto.moneda = data['moneda']
        db.session.commit()
        return jsonify(gasto.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/ingresos/<int:id>', methods=['PUT'])
def actualizar_ingreso(id):
    try:
        ingreso = db.session.get(Ingreso, id)
        if not ingreso:
            return jsonify({"error": "Ingreso no encontrado."}), 404
        data = request.get_json(silent=True) or {}
        if data.get('monto'):  ingreso.monto = float(data['monto'])
        if data.get('fuente'): ingreso.fuente = data['fuente']
        if data.get('fecha'):  ingreso.fecha = datetime.strptime(data['fecha'], '%Y-%m-%d').date()
        db.session.commit()
        return jsonify({"id": ingreso.id, "monto": ingreso.monto, "fuente": ingreso.fuente, "fecha": ingreso.fecha.strftime('%Y-%m-%d')}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/ingresos/<int:id>', methods=['DELETE'])
def eliminar_ingreso(id):
    try:
        ingreso = db.session.get(Ingreso, id)
        if not ingreso:
            return jsonify({"error": "Ingreso no encontrado."}), 404
        db.session.delete(ingreso)
        db.session.commit()
        return jsonify({"mensaje": "Ingreso eliminado."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/presupuestos/<int:id>', methods=['PUT'])
def actualizar_presupuesto(id):
    try:
        p = db.session.get(Presupuesto, id)
        if not p:
            return jsonify({"error": "Presupuesto no encontrado."}), 404
        data = request.get_json(silent=True) or {}
        if data.get('monto_limite'): p.monto_limite = float(data['monto_limite'])
        if data.get('categoria'):    p.categoria = data['categoria']
        db.session.commit()
        return jsonify({"id": p.id, "categoria": p.categoria, "monto_limite": p.monto_limite}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/presupuestos/<int:id>', methods=['DELETE'])
def eliminar_presupuesto(id):
    try:
        p = db.session.get(Presupuesto, id)
        if not p:
            return jsonify({"error": "Presupuesto no encontrado."}), 404
        db.session.delete(p)
        db.session.commit()
        return jsonify({"mensaje": "Presupuesto eliminado."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/fijos/<int:id>', methods=['PUT'])
def actualizar_fijo(id):
    try:
        f = db.session.get(GastoFijo, id)
        if not f:
            return jsonify({"error": "Gasto fijo no encontrado."}), 404
        data = request.get_json(silent=True) or {}
        if data.get('nombre'):    f.nombre = data['nombre']
        if data.get('monto'):     f.monto = float(data['monto'])
        if data.get('categoria'): f.categoria = data['categoria']
        if 'pagado' in data:      f.pagado = bool(data['pagado'])
        db.session.commit()
        return jsonify({"id": f.id, "nombre": f.nombre, "monto": f.monto, "categoria": f.categoria, "pagado": f.pagado}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/fijos/<int:id>', methods=['DELETE'])
def eliminar_fijo_v2(id):
    try:
        f = db.session.get(GastoFijo, id)
        if not f:
            return jsonify({"error": "Gasto fijo no encontrado."}), 404
        db.session.delete(f)
        db.session.commit()
        return jsonify({"mensaje": "Gasto fijo eliminado."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_financiero():
    if not client:
        return jsonify({"error": "La API Key de Gemini no está configurada."}), 500

    data = request.json
    pregunta = data.get('pregunta')
    if not pregunta:
        return jsonify({"error": "No se proporcionó ninguna pregunta."}), 400

    try:
        gastos = Gasto.query.all()
        if not gastos:
            return jsonify({"respuesta": "Aún no tienes gastos registrados para analizar."}), 200

        lista_gastos = "\n".join([f"- Fecha: {g.fecha}, Comercio: {g.comercio}, Categoría: {g.categoria}, Monto: {g.monto} {g.moneda}" for g in gastos])

        ingresos = Ingreso.query.all()
        lista_ingresos = "\n".join([f"- Fecha: {i.fecha}, Fuente: {i.fuente}, Monto: {i.monto}" for i in ingresos])
        
        presupuestos = Presupuesto.query.all()
        lista_presupuestos = "\n".join([f"- Categoría: {p.categoria}, Límite: {p.monto_limite}" for p in presupuestos])

        fijos = GastoFijo.query.all()
        lista_fijos = "\n".join([f"- {f.nombre}: {f.monto}€ ({f.categoria})" for f in fijos])

        total_ingresos = sum(i.monto for i in ingresos)
        total_gastos = sum(g.monto for g in gastos) + sum(f.monto for f in fijos)
        balance_real = total_ingresos - total_gastos

        prompt = f"""
        Eres un analista financiero experto y amigable llamado 'GastoGenie'.
        Tienes acceso a la situación financiera completa del usuario:
        
        DATOS DE INGRESOS:
        {lista_ingresos if ingresos else "No hay ingresos registrados."}
        
        GASTOS FIJOS (OBLIGATORIOS):
        {lista_fijos if fijos else "No hay gastos fijos registrados."}
        
        PRESUPUESTOS POR CATEGORÍA:
        {lista_presupuestos if presupuestos else "No hay presupuestos definidos."}
        
        HISTORIAL DE GASTOS VARIABLES:
        {lista_gastos}
        
        RESUMEN ACTUAL:
        - Total Ingresos: {total_ingresos}€
        - Balance Real (Ingresos - Todos los gastos): {balance_real}€
        
        Responde a la duda del usuario de forma clara, motivadora y basada exclusivamente en estos datos: 
        [{pregunta}]
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return jsonify({"respuesta": response.text.strip()}), 200
    except Exception as e:
        print(f"Error procesando chat: {e}")
        return jsonify({"error": "Error interno al consultar el asistente.", "detalle": str(e)}), 500

@app.route('/api/ingresos', methods=['POST', 'GET'])
def gestionar_ingresos():
    if request.method == 'POST':
        # Soporta JSON y multipart/form-data
        data = request.get_json(silent=True) or request.form
        try:
            nuevo = Ingreso(
                monto=float(data.get('monto', 0)),
                fuente=data.get('fuente', 'Sin fuente'),
                fecha=data.get('fecha') or datetime.now().strftime('%Y-%m-%d'),
                es_nomina=str(data.get('es_nomina', 'true')).lower() == 'true'
            )
            db.session.add(nuevo)
            db.session.commit()
            return jsonify({"mensaje": "Ingreso registrado", "id": nuevo.id}), 201
        except Exception as e:
            db.session.rollback()
            print(f"Error guardando ingreso: {e}")
            return jsonify({"error": "Error al guardar el ingreso.", "detalle": str(e)}), 400
    # GET
    try:
        ingresos = Ingreso.query.order_by(Ingreso.fecha.desc()).all()
        return jsonify([{"id": i.id, "monto": i.monto, "fuente": i.fuente, "fecha": i.fecha.strftime('%Y-%m-%d'), "es_nomina": i.es_nomina} for i in ingresos])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/presupuestos', methods=['POST', 'GET'])
def gestionar_presupuestos():
    if request.method == 'POST':
        data = request.get_json(silent=True)
        try:
            mes = int(data.get('mes', datetime.now().month))
            anio = int(data.get('año', datetime.now().year))
            p = Presupuesto.query.filter_by(
                categoria=data.get('categoria'), mes=mes, año=anio
            ).first()
            if p:
                p.monto_limite = float(data.get('monto_limite'))
            else:
                p = Presupuesto(
                    categoria=data.get('categoria'),
                    monto_limite=float(data.get('monto_limite')),
                    mes=mes,
                    año=anio
                )
                db.session.add(p)
            db.session.commit()
            return jsonify({"mensaje": "Presupuesto actualizado"}), 200
        except Exception as e:
            db.session.rollback()
            print(f"Error guardando presupuesto: {e}")
            return jsonify({"error": "Error al guardar el presupuesto.", "detalle": str(e)}), 400
    # GET
    try:
        presupuestos = Presupuesto.query.all()
        return jsonify([{"id": p.id, "categoria": p.categoria, "monto_limite": p.monto_limite, "mes": p.mes, "año": p.año} for p in presupuestos])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/fijos', methods=['POST', 'GET'])
def gestionar_fijos():
    if request.method == 'POST':
        data = request.get_json(silent=True)
        try:
            nuevo = GastoFijo(
                nombre=data.get('nombre'),
                monto=float(data.get('monto', 0)),
                categoria=data.get('categoria', 'Hogar'),
                pagado=bool(data.get('pagado', False))
            )
            db.session.add(nuevo)
            db.session.commit()
            return jsonify({"mensaje": "Gasto fijo añadido", "id": nuevo.id}), 201
        except Exception as e:
            db.session.rollback()
            print(f"Error guardando gasto fijo: {e}")
            return jsonify({"error": "Error al guardar el gasto fijo.", "detalle": str(e)}), 400

    # GET
    try:
        fijos = GastoFijo.query.all()
        return jsonify([{"id": f.id, "nombre": f.nombre, "monto": f.monto, "categoria": f.categoria, "pagado": f.pagado} for f in fijos])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/balance', methods=['GET'])
def obtener_balance():
    try:
        total_ingresos = db.session.query(db.func.sum(Ingreso.monto)).scalar() or 0
        total_fijos = db.session.query(db.func.sum(GastoFijo.monto)).scalar() or 0
        total_variables = db.session.query(db.func.sum(Gasto.monto)).scalar() or 0
        return jsonify({
            "total_ingresos": float(total_ingresos),
            "total_fijos": float(total_fijos),
            "total_variables": float(total_variables),
            "saldo_real": float(total_ingresos - total_fijos - total_variables)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/resumen_financiero', methods=['GET'])
def resumen_financiero():
    """Endpoint dedicado con el resumen financiero completo del usuario."""
    try:
        total_ingresos = db.session.query(db.func.sum(Ingreso.monto)).scalar() or 0
        total_gastos_var = db.session.query(db.func.sum(Gasto.monto)).scalar() or 0
        total_gastos_fijos = db.session.query(db.func.sum(GastoFijo.monto)).scalar() or 0
        total_gastos = total_gastos_var + total_gastos_fijos
        balance_final = total_ingresos - total_gastos

        # Calcula porcentaje gastado respecto al total de ingresos
        pct_gastado = round((total_gastos / total_ingresos * 100), 1) if total_ingresos > 0 else 0

        return jsonify({
            "total_ingresos": float(total_ingresos),
            "total_gastos": float(total_gastos),
            "total_gastos_variables": float(total_gastos_var),
            "total_gastos_fijos": float(total_gastos_fijos),
            "balance_final": float(balance_final),
            "presupuesto_gastado_porcentaje": pct_gastado
        })
    except Exception as e:
        print(f"Error en resumen_financiero: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/objetivos', methods=['GET', 'POST'])
def gestionar_objetivos():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        try:
            obj = ObjetivoAhorro(
                nombre=data.get('nombre', 'Mi Objetivo'),
                meta_monto=float(data.get('meta_monto', 0)),
                monto_actual=float(data.get('monto_actual', 0)),
                fecha_limite=data.get('fecha_limite')
            )
            db.session.add(obj)
            db.session.commit()
            return jsonify(obj.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400
    try:
        objetivos = ObjetivoAhorro.query.all()
        return jsonify([o.to_dict() for o in objetivos])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/objetivos/<int:id>', methods=['PUT', 'DELETE'])
def gestionar_objetivo(id):
    obj = db.session.get(ObjetivoAhorro, id)
    if not obj:
        return jsonify({"error": "Objetivo no encontrado."}), 404
    if request.method == 'DELETE':
        try:
            db.session.delete(obj)
            db.session.commit()
            return jsonify({"mensaje": "Objetivo eliminado."}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
    # PUT — abonar o editar
    data = request.get_json(silent=True) or {}
    try:
        if 'nombre' in data:      obj.nombre = data['nombre']
        if 'meta_monto' in data:  obj.meta_monto = float(data['meta_monto'])
        if 'monto_actual' in data: obj.monto_actual = float(data['monto_actual'])
        if 'fecha_limite' in data and data['fecha_limite']:
            obj.fecha_limite = datetime.strptime(data['fecha_limite'], '%Y-%m-%d').date()
        db.session.commit()
        return jsonify(obj.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/historico_mensual', methods=['GET'])
def historico_mensual():
    """Devuelve ingresos y gastos agregados por mes (últimos 5 meses)."""
    try:
        from datetime import date
        hoy = date.today()
        meses = []
        for i in range(4, -1, -1):
            mes = (hoy.month - i - 1) % 12 + 1
            anio = hoy.year - ((hoy.month - i - 1) // 12)
            meses.append((anio, mes))

        resultado = []
        for anio, mes in meses:
            gastos_mes = db.session.query(db.func.sum(Gasto.monto)).filter(
                db.extract('year', Gasto.fecha) == anio,
                db.extract('month', Gasto.fecha) == mes
            ).scalar() or 0

            ingresos_mes = db.session.query(db.func.sum(Ingreso.monto)).filter(
                db.extract('year', Ingreso.fecha) == anio,
                db.extract('month', Ingreso.fecha) == mes
            ).scalar() or 0

            resultado.append({
                "mes": f"{mes:02d}/{anio}",
                "gastos": float(gastos_mes),
                "ingresos": float(ingresos_mes)
            })
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analisis_avanzado', methods=['GET'])
def analisis_avanzado():
    """Análisis financiero avanzado con IA: predicción, gastos hormiga y consejos."""
    if not client:
        return jsonify({"error": "Gemini API Key no configurada."}), 500
    try:
        hoy = datetime.now()
        mes_actual = hoy.month
        anio_actual = hoy.year
        dias_transcurridos = hoy.day
        dias_en_mes = 31  # Aproximación conservadora

        # Gastos del mes actual
        gastos_mes = Gasto.query.filter(
            db.extract('year', Gasto.fecha) == anio_actual,
            db.extract('month', Gasto.fecha) == mes_actual
        ).all()
        total_gastado_mes = sum(g.monto for g in gastos_mes)

        # Ingresos del mes actual
        total_ingresos_mes = db.session.query(db.func.sum(Ingreso.monto)).filter(
            db.extract('year', Ingreso.fecha) == anio_actual,
            db.extract('month', Ingreso.fecha) == mes_actual
        ).scalar() or 0

        # Proyección de gasto a fin de mes
        ritmo_diario = total_gastado_mes / dias_transcurridos if dias_transcurridos > 0 else 0
        proyeccion_fin_mes = ritmo_diario * dias_en_mes

        # Gastos hormiga: monto <= 10€ y comercio repetido >= 3 veces (todos los tiempos)
        from collections import Counter
        todos_gastos = Gasto.query.all()
        pequenos = [g for g in todos_gastos if g.monto <= 10]
        conteo = Counter(g.comercio for g in pequenos)
        hormiga = [{"comercio": c, "veces": n, "monto_unitario": next(g.monto for g in pequenos if g.comercio == c), "ahorro_anual": next(g.monto for g in pequenos if g.comercio == c) * n * 12 / max(len(todos_gastos)//12, 1)} for c, n in conteo.items() if n >= 3]

        # Objetivos de ahorro
        objetivos = ObjetivoAhorro.query.all()
        lista_objetivos = "\n".join([f"- {o.nombre}: {o.monto_actual}/{o.meta_monto}€ ({o.to_dict()['porcentaje']}%)" for o in objetivos]) or "Sin objetivos definidos."

        prompt = f"""
        Eres GastoGenie, un analista financiero experto. Analiza estos datos y genera un JSON con exactamente estas 3 claves:

        DATOS:
        - Mes actual: {hoy.strftime('%B %Y')}
        - Días transcurridos: {dias_transcurridos}/{dias_en_mes}
        - Total gastado este mes: {total_gastado_mes:.2f}€
        - Ingresos este mes: {float(total_ingresos_mes):.2f}€
        - Ritmo diario de gasto: {ritmo_diario:.2f}€/día
        - Proyección de gasto a fin de mes: {proyeccion_fin_mes:.2f}€
        - Gastos hormiga identificados: {hormiga}
        - Objetivos de ahorro: {lista_objetivos}

        Genera SOLO un JSON válido (sin markdown) con esta estructura exacta:
        {{
            "prediccion": "Texto conciso de 2-3 frases sobre la predicción del saldo a fin de mes.",
            "gastos_hormiga": "Texto identificando los gastos hormiga más impactantes y el ahorro potencial anual.",
            "consejo_ahorro": "Un consejo motivador y específico sobre los objetivos de ahorro activos."
        }}
        """

        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        content = response.text.strip()
        if content.startswith('```json'): content = content[7:-3].strip()
        elif content.startswith('```'):  content = content[3:-3].strip()

        ai_data = {}
        try:
            ai_data = json.loads(content)
        except Exception:
            ai_data = {"prediccion": content, "gastos_hormiga": "", "consejo_ahorro": ""}

        return jsonify({
            "mes": hoy.strftime('%B %Y'),
            "total_gastado_mes": float(total_gastado_mes),
            "total_ingresos_mes": float(total_ingresos_mes),
            "proyeccion_fin_mes": float(proyeccion_fin_mes),
            "gastos_hormiga_raw": hormiga,
            "prediccion": ai_data.get("prediccion", ""),
            "gastos_hormiga": ai_data.get("gastos_hormiga", ""),
            "consejo_ahorro": ai_data.get("consejo_ahorro", "")
        }), 200
    except Exception as e:
        print(f"Error en analisis_avanzado: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    try:
        resultados = db.session.query(
            Gasto.categoria, 
            db.func.sum(Gasto.monto).label('total')
        ).group_by(Gasto.categoria).all()
        
        datos = [{"categoria": r.categoria, "total": float(r.total)} for r in resultados]
        return jsonify(datos), 200
    except Exception as e:
        return jsonify({"error": "Error al obtener estadísticas.", "detalle": str(e)}), 500

@app.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)

if __name__ == '__main__':
    app.run(debug=True, port=5000)