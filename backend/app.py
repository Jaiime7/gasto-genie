from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
# CORS permite que el frontend (Vue) se comunique con este backend
CORS(app)

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"mensaje": "¡Backend de Flask funcionando a la perfección!"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)