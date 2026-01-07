from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from PIL import Image, ExifTags
import uuid
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Конфигурация для продакшена
app.config.update(
    UPLOAD_FOLDER='uploads',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif'},
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
)

# Создаем папку для загрузок
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Отключаем кэширование в разработке
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_gps_from_exif(image_path):
    """Извлекаем GPS координаты из EXIF"""
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            
            if not exif_data:
                return None
            
            for tag_id, value in exif_data.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                if tag == 'GPSInfo':
                    gps_info = {}
                    for gps_tag in value:
                        sub_tag = ExifTags.GPSTAGS.get(gps_tag, gps_tag)
                        gps_info[sub_tag] = value[gps_tag]
                    
                    def convert_to_degrees(value):
                        if isinstance(value, tuple):
                            d, m, s = value
                            return d + (m / 60.0) + (s / 3600.0)
                        return float(value)
                    
                    if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
                        lat = convert_to_degrees(gps_info['GPSLatitude'])
                        if gps_info.get('GPSLatitudeRef') == 'S':
                            lat = -lat
                        
                        lon = convert_to_degrees(gps_info['GPSLongitude'])
                        if gps_info.get('GPSLongitudeRef') == 'W':
                            lon = -lon
                        
                        return {
                            'latitude': lat,
                            'longitude': lon,
                            'altitude': gps_info.get('GPSAltitude', 0)
                        }
    except Exception as e:
        logger.error(f"Ошибка при чтении EXIF: {e}")
    
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'service': 'PhotoLocator',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/analyze', methods=['POST'])
def analyze_photo():
    try:
        if 'photo' not in request.files:
            return jsonify({'error': 'Файл не выбран'}), 400
        
        file = request.files['photo']
        
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'Неподдерживаемый формат файла. Используйте JPG, PNG, GIF'
            }), 400
        
        # Генерируем уникальное имя
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        logger.info(f"Файл загружен: {unique_filename}")
        
        # Анализ изображения
        with Image.open(filepath) as img:
            width, height = img.size
            format = img.format
        
        # Получаем GPS данные
        gps_data = get_gps_from_exif(filepath)
        
        response = {
            'success': True,
            'filename': unique_filename,
            'image_info': {
                'width': width,
                'height': height,
                'format': format
            }
        }
        
        if gps_data:
            response['location'] = {
                'latitude': gps_data['latitude'],
                'longitude': gps_data['longitude'],
                'altitude': gps_data['altitude'],
                'source': 'gps_exif',
                'address': f'Координаты: {gps_data["latitude"]:.6f}, {gps_data["longitude"]:.6f}'
            }
            response['map_url'] = f'https://www.openstreetmap.org/?mlat={gps_data["latitude"]}&mlon={gps_data["longitude"]}'
        else:
            response['location'] = {
                'latitude': 55.7558,
                'longitude': 37.6176,
                'source': 'demo',
                'address': 'Москва, Россия (демо-данные)',
                'note': 'В этой фотографии нет GPS данных. Показаны демо-координаты'
            }
            response['map_url'] = 'https://www.openstreetmap.org/?mlat=55.7558&mlon=37.6176'
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Ошибка обработки: {str(e)}")
        return jsonify({'error': f'Ошибка обработки: {str(e)}'}), 500

# Обработчики ошибок
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Страница не найдена'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
