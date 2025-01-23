from flask import Flask, send_from_directory, abort, jsonify, request
import os
import shutil
from flask_cors import CORS

app = Flask(__name__)

CORS(app)

IMAGE_FOLDER = os.path.join(os.getcwd(), 'static', 'images')
LABELED_FOLDER = os.path.join(IMAGE_FOLDER, 'labeled')
app.config['IMAGE_FOLDER'] = IMAGE_FOLDER
app.config['LABELED_FOLDER'] = LABELED_FOLDER

# Asegurarse de que la carpeta 'labeled' exista
os.makedirs(LABELED_FOLDER, exist_ok=True)

def get_images_list():
    try:
        return [f for f in os.listdir(app.config['IMAGE_FOLDER']) if os.path.isfile(os.path.join(app.config['IMAGE_FOLDER'], f))]
    except Exception as e:
        print(f"Error al obtener las imágenes: {e}")
        return []

@app.route('/images', methods=['GET'])
def get_images():
    page = request.args.get('page', default=1, type=int)
    per_page = 5
    images = get_images_list()
    start = (page - 1) * per_page
    end = start + per_page
    images_page = images[start:end]
    if not images_page:
        return jsonify({"error": "No hay más imágenes en esta página."}), 404
    return jsonify(images=images_page)

@app.route('/image/<image_name>', methods=['GET'])
def get_image(image_name):
    try:
        if image_name in get_images_list():
            return send_from_directory(app.config['IMAGE_FOLDER'], image_name)
        else:
            abort(404)
    except Exception as e:
        print(f"Error al obtener la imagen: {e}")
        abort(404)

# Nuevo endpoint para mover la imagen y guardar las etiquetas en formato YOLO
@app.route('/label-image', methods=['POST'])
def label_image():
    data = request.get_json()

    # Obtener la información de la imagen, las etiquetas y las posiciones
    image_name = data.get('imageName')
    tags = data.get('tags')  # [{name, x, y}]
    
    # Verificar que la imagen existe
    if image_name not in get_images_list():
        return jsonify({"error": "La imagen no existe."}), 404

    # Mover la imagen a la carpeta 'labeled'
    original_image_path = os.path.join(app.config['IMAGE_FOLDER'], image_name)
    labeled_image_path = os.path.join(app.config['LABELED_FOLDER'], image_name)

    try:
        shutil.move(original_image_path, labeled_image_path)
    except Exception as e:
        return jsonify({"error": f"No se pudo mover la imagen: {e}"}), 500

    # Crear el archivo de anotación en formato YOLO
    label_file_path = os.path.join(app.config['LABELED_FOLDER'], f"{os.path.splitext(image_name)[0]}.txt")
    with open(label_file_path, 'w') as label_file:
        for tag in tags:
            # Asumimos que cada tag tiene la estructura {name, x, y}
            # Convertimos las coordenadas (x, y) a formato YOLO: clase, x_center, y_center, width, height
            # Los valores de (x, y) deben estar normalizados según el tamaño de la imagen
            # Por ejemplo, si la imagen es de 1920x1080, 960px de ancho sería 0.5 en YOLO

            # Aquí se asume que las clases están representadas por números (por ejemplo, 'Personaje' = 0, 'Vehículo' = 1, etc.)
            class_mapping = {'Personaje': 0, 'Vehículo': 1, 'Objeto': 2, 'Fondo': 3}
            label_class = class_mapping.get(tag['name'])

            if label_class is not None:
                label_file.write(f"{label_class} {tag['x']} {tag['y']} 0 0\n")  # Asumiendo que solo se pasa (x, y)
            else:
                return jsonify({"error": "Etiqueta desconocida."}), 400

    return jsonify({"message": "Imagen etiquetada y movida con éxito."})

if __name__ == '__main__':
    app.run(debug=True)
