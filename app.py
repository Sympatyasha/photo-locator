from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import uuid
from datetime import datetime
import base64
from io import BytesIO

app = Flask(__name__)

# Конфигурация
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Простой HTML без сложных зависимостей
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PhotoLocator - Определение местоположения по фото</title>
    <style>
        body { font-family: Arial; padding: 20px; max-width: 800px; margin: 0 auto; }
        .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }
        .result { margin-top: 20px; padding: 20px; background: #f5f5f5; }
    </style>
</head>
<body>
    <h1>📍 PhotoLocator</h1>
    <p>Загрузите фотографию для определения местоположения</p>
    
    <div class="upload-area">
        <input type="file" id="photoInput" accept="image/*">
        <button onclick="uploadPhoto()">Анализировать</button>
    </div>
    
    <div class="result" id="result" style="display:none;">
        <h3>Результаты:</h3>
        <p id="location"></p>
        <a id="mapLink" target="_blank">Открыть на карте</a>
    </div>
    
    <script>
    async function uploadPhoto() {
        const input = document.getElementById('photoInput');
        if (!input.files[0]) return alert('Выберите файл');
        
        const formData = new FormData();
        formData.append('photo', input.files[0]);
        
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('location').textContent = 
                `Адрес: ${data.location.address}`;
            document.getElementById('mapLink').href = data.map_url;
            document.getElementById('result').style.display = 'block';
        } else {
            alert('Ошибка: ' + data.error);
        }
    }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if 'photo' not in request.files:
            return jsonify({'error': 'Файл не выбран'}), 400
        
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        # Сохраняем файл
        filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Возвращаем тестовые данные (без Pillow)
        return jsonify({
            'success': True,
            'filename': filename,
            'location': {
                'latitude': 55.7558,
                'longitude': 37.6176,
                'address': 'Москва, Россия (тестовые данные)',
                'source': 'demo'
            },
            'map_url': 'https://www.openstreetmap.org/?mlat=55.7558&mlon=37.6176'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'PhotoLocator'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
