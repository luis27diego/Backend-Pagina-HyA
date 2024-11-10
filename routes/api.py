from flask import Blueprint, jsonify, request
from .auth import token_required
import psycopg2
from dotenv import load_dotenv
from config import Config

# Crear un Blueprint para las rutas de la API
api_bp = Blueprint('api', __name__)

# Cargar variables de entorno desde el archivo .env
load_dotenv()

def get_db_connection():
    config = Config()
    conn = psycopg2.connect(config.DATABASE_URL)
    return conn

@api_bp.route('/subtitulos_con_detalles', methods=['GET'])
def get_subtitulos_con_detalles():
    pagina_id = request.args.get('paginaId')
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener subtítulos
    if pagina_id:
        cursor.execute("SELECT * FROM subtitulos WHERE ID_PAGINA = %s ORDER BY Orden", (pagina_id,))
    else:
        cursor.execute("SELECT * FROM subtitulos")
    
    subtitulos = cursor.fetchall()

    subtitulos_list = []
    for subtitulo in subtitulos:
        subtitulo_id = subtitulo[0]
        subtitulo_data = {
            "ID_SUBTITULO": subtitulo_id,
            "TITULO": subtitulo[1],
            "ID_PAGINA": subtitulo[3],
            "DETALLES": []
        }

        # Obtener detalles para cada subtítulo
        cursor.execute("SELECT * FROM detalles WHERE ID_SUBTITULOS = %s", (subtitulo_id,))
        detalles = cursor.fetchall()
        for detalle in detalles:
            detalle_id = detalle[0]
            detalle_data = {
                "ID_DETALLES": detalle_id,
                "DEFINICION": detalle[1],
                "IMAGENES": []
            }

            # Obtener imágenes y sus captions para cada detalle
            cursor.execute("SELECT URL_IMAGEN, CAPTION FROM imagenes WHERE ID_DETALLES = %s", (detalle_id,))
            imagenes = cursor.fetchall()
            for imagen in imagenes:
                imagen_data = {
                    "URL_IMAGEN": imagen[0],
                    "CAPTION": imagen[1]
                }
                detalle_data["IMAGENES"].append(imagen_data)

            subtitulo_data["DETALLES"].append(detalle_data)
        
        subtitulos_list.append(subtitulo_data)
    
    cursor.close()
    conn.close()

    return jsonify(subtitulos_list)

    
@api_bp.route('/editar_subtitulo/<int:subtitulo_id>', methods=['POST'])
def editar_subtitulo(subtitulo_id):
    title = request.form.get('title')

    # Usar un diccionario para almacenar definiciones, imágenes y sus IDs
    definitions = {}
    images = {}
    for key in request.form.keys():
        if 'details[' in key and '][definition]' in key:
            # Extraer el ID desde el key
            index = key.split('details[')[1].split('][definition]')[0]
            definitions[index] = request.form.get(key)
        
        if 'details[' in key and '][image]' in key:
            # Extraer el ID y almacenar la imagen
            index = key.split('details[')[1].split('][image]')[0]
            images[index] = request.files.get(key)

    if not title or not definitions:
        return jsonify({"error": "Title and definitions are required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Actualizar el título del subtítulo en la base de datos
        cursor.execute("""
            UPDATE subtitulos
            SET TITULO = %s
            WHERE ID_SUBTITULO = %s
        """, (title, subtitulo_id))

        # Actualizar cada definición correspondiente
        for index, definition in definitions.items():
            cursor.execute("""
                UPDATE detalles
                SET DEFINICION = %s
                WHERE ID_SUBTITULOS = %s AND ID_DETALLES = %s
            """, (definition, subtitulo_id, index))  # Usar el ID_DETALLES

            # Si hay una nueva imagen, procesarla
            if index in images and images[index]:
                image = images[index]
                # Guardar la imagen en el servidor (esto es solo un ejemplo)
                image_url = f"/path/to/save/{image.filename}"
                image.save(image_url)

                # Actualizar la imagen en la base de datos
                cursor.execute("""
                    UPDATE imagenes
                    SET URL_IMAGEN = %s
                    WHERE ID_DETALLES = %s
                """, (image_url, index))  # Usar el ID_DETALLES

        conn.commit()
        return jsonify({"message": "Subtítulo actualizado correctamente"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@api_bp.route('/sugerir_definicion', methods=['POST'])
def sugerir_definicion():
    print(request.form)  # Ver qué llega al backend
    title = request.form.get('title')
    id_usuario = 1  # Asegúrate de obtener esto del formulario o sesión si es dinámico

    definitions = {}

    # Recopilar definiciones del formulario
    for key in request.form.keys():
        if 'details[' in key and '][definition]' in key:
            index = key.split('details[')[1].split('][definition]')[0]
            definitions[index] = request.form.get(key)

    # Validar que haya un título y al menos una definición
    if not title or not definitions:
        return jsonify({"error": "El título y las definiciones son requeridos"}), 400

    # Conectar a la base de datos
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Obtener el título actual del subtítulo
        query_get_subtitulo_actual = """
            SELECT titulo FROM subtitulos WHERE id_subtitulo = (
                SELECT id_subtitulos FROM detalles WHERE id_detalles = %s LIMIT 1
            )
        """
        cur.execute(query_get_subtitulo_actual, (list(definitions.keys())[0],))  # Usamos el primer id_detalle
        current_title = cur.fetchone()[0]

        # Verificar si el título actual es diferente del sugerido
        if current_title != title:
            query_check_title_suggestion = """
                SELECT COUNT(*) FROM sugerencias
                WHERE id_usuario = %s AND id_detalle = %s AND titulo_subtitulo_sugerido = %s AND estado = 'pendiente'
            """
            cur.execute(query_check_title_suggestion, (id_usuario, list(definitions.keys())[0], title))
            title_exists = cur.fetchone()[0]

            if title_exists == 0:
                # Insertar sugerencia de cambio de título
                query_title_suggestion = """
                    INSERT INTO sugerencias (id_usuario, id_detalle, titulo_subtitulo_sugerido, tipo_cambio, estado, fecha_envio)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """
                cur.execute(query_title_suggestion, (id_usuario, list(definitions.keys())[0], title, 'subtitulo', 'pendiente'))
            else:
                print("Ya existe una sugerencia pendiente para este título.")

        # Verificar si ya existe una sugerencia pendiente para cada definición
        for index, definition in definitions.items():
            # Obtener la definición actual
            query_get_definition_actual = """
                SELECT definicion FROM detalles WHERE id_detalles = %s
            """
            cur.execute(query_get_definition_actual, (index,))
            current_definition = cur.fetchone()[0]

            # Verificar si la definición actual es diferente de la sugerida
            if current_definition != definition:
                query_check_definition_suggestion = """
                    SELECT COUNT(*) FROM sugerencias
                    WHERE id_usuario = %s AND id_detalle = %s AND definicion = %s AND estado = 'pendiente'
                """
                cur.execute(query_check_definition_suggestion, (id_usuario, index, definition))
                definition_exists = cur.fetchone()[0]

                if definition_exists == 0:
                    # Insertar sugerencia de definición
                    query_definition_suggestion = """
                        INSERT INTO sugerencias (id_usuario, id_detalle, definicion, tipo_cambio, estado, fecha_envio)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """
                    cur.execute(query_definition_suggestion, (id_usuario, index, definition, 'definicion', 'pendiente'))
                else:
                    print(f"Ya existe una sugerencia pendiente para la definición en id_detalle={index}.")
            else:
                print(f"La definición actual y la sugerida son iguales para id_detalle={index}. No se necesita sugerir.")

        # Confirmar los cambios en la base de datos
        conn.commit()

        return jsonify({"message": "Sugerencia enviada exitosamente"}), 200

    except Exception as e:
        # Deshacer la transacción en caso de error
        conn.rollback()
        print(f"Error en la base de datos: {e}")
        return jsonify({"error": "Error en el servidor: " + str(e)}), 500

    finally:
        # Cerrar el cursor y la conexión
        cur.close()
        conn.close()



@api_bp.route('/obtener_sugerencias', methods=['GET'])
@token_required
def obtener_sugerencias(current_user):  # current_user es el ID del usuario obtenido del token
    # Imprimir la información del usuario actual
    print(f"Usuario actual: {current_user}")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = """
            SELECT 
                sug.id_sugerencia, 
                sug.id_usuario, 
                sug.id_detalle, 
                sug.definicion, 
                sug.titulo_subtitulo_sugerido, 
                sug.tipo_cambio, 
                sug.estado, 
                sug.fecha_envio, 
                det.id_subtitulos, 
                sub.titulo AS nombre_subtitulo, 
                pag.titulo AS titulo_pagina,
                tej.nombre AS nombre_tejido
            FROM 
                sugerencias sug
            JOIN 
                detalles det ON sug.id_detalle = det.id_detalles
            JOIN 
                subtitulos sub ON det.id_subtitulos = sub.id_subtitulo
            JOIN 
                pagina pag ON sub.id_pagina = pag.id_pagina
            JOIN 
                tejidos tej ON pag.id_tejido = tej.id_tejido
            WHERE 
                sug.estado = 'pendiente';
        """
        cur.execute(query)
        sugerencias = cur.fetchall()
        
        resultado = []
        for sugerencia in sugerencias:
            resultado.append({
                'id_sugerencia': sugerencia[0],
                'id_usuario': sugerencia[1],
                'id_detalle': sugerencia[2],
                'definicion': sugerencia[3],
                'titulo_subtitulo_sugerido': sugerencia[4],
                'tipo_cambio': sugerencia[5],
                'estado': sugerencia[6],
                'fecha_envio': sugerencia[7].strftime('%Y-%m-%d %H:%M:%S'),
                'id_subtitulo': sugerencia[8],
                'nombre_subtitulo': sugerencia[9],
                'titulo_pagina': sugerencia[10],
                'nombre_tejido': sugerencia[11]
            })
        return jsonify(resultado), 200
    except Exception as e:
        print(f"Error al obtener sugerencias: {e}")
        return jsonify({"error": "Error al obtener sugerencias"}), 500
    finally:
        cur.close()
        conn.close()




@api_bp.route('/aprobar_rechazar_sugerencia/<int:id_sugerencia>', methods=['POST'])
def aprobar_rechazar_sugerencia(id_sugerencia):
    # Obtener si se aprueba o rechaza la sugerencia desde el formulario
    estado = request.form.get('estado')  # 'aceptada' o 'rechazada'

    # Validar el estado
    if estado not in ['aceptada', 'rechazada']:
        return jsonify({"error": "Estado inválido"}), 400

    # Conectar a la base de datos
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Actualizar el estado de la sugerencia
        query = "UPDATE sugerencias SET estado = %s WHERE id_sugerencia = %s"
        cur.execute(query, (estado, id_sugerencia))

        # Si la sugerencia es aceptada, podrías actualizar la definición en la tabla correspondiente
        if estado == 'aceptada':
            # Asumimos que tienes una tabla `definiciones` donde se guarda la definición final
            query_actualizar_definicion = """
                UPDATE detalles
                SET definicion = (
                    SELECT definicion FROM sugerencias WHERE id_sugerencia = %s
                )
                WHERE id_detalle = (
                    SELECT id_detalle FROM sugerencias WHERE id_sugerencia = %s
                )
            """
            cur.execute(query_actualizar_definicion, (id_sugerencia, id_sugerencia))

        # Confirmar los cambios en la base de datos
        conn.commit()

        return jsonify({"message": "Sugerencia actualizada correctamente"}), 200

    except Exception as e:
        # En caso de error, deshacer los cambios
        conn.rollback()
        return jsonify({"error": "Error al procesar la sugerencia: " + str(e)}), 500

    finally:
        # Cerrar el cursor y la conexión
        cur.close()
        conn.close()

@api_bp.route('/aprobar_sugerencia/<int:id_sugerencia>', methods=['POST'])
def aprobar_sugerencia(id_sugerencia):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Actualizar el estado de la sugerencia a 'aceptada'
        query = "UPDATE sugerencias SET estado = 'aceptada' WHERE id_sugerencia = %s"
        cur.execute(query, (id_sugerencia,))

        # Actualizar la definición en la tabla detalles correspondiente
        query_actualizar_definicion = """
            UPDATE detalles
            SET definicion = (
                SELECT definicion FROM sugerencias WHERE id_sugerencia = %s
            )
            WHERE id_detalles = (
                SELECT id_detalle FROM sugerencias WHERE id_sugerencia = %s
            )
        """
        cur.execute(query_actualizar_definicion, (id_sugerencia, id_sugerencia))

        # Actualizar el título en la tabla subtitulo solo si el nuevo título no es NULL
        query_actualizar_titulo = """
            UPDATE subtitulos
            SET titulo = (
                SELECT titulo_subtitulo_sugerido FROM sugerencias WHERE id_sugerencia = %s
            )
            WHERE subtitulos.id_subtitulo = (
                SELECT detalles.id_subtitulos
                FROM detalles
                JOIN sugerencias ON detalles.id_detalles = sugerencias.id_detalle
                WHERE sugerencias.id_sugerencia = %s
            ) AND (
                SELECT titulo_subtitulo_sugerido FROM sugerencias WHERE id_sugerencia = %s
            ) IS NOT NULL
        """
        cur.execute(query_actualizar_titulo, (id_sugerencia, id_sugerencia, id_sugerencia))

        # Confirmar los cambios
        conn.commit()

        return jsonify({"message": "Sugerencia aprobada correctamente"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Error al aprobar sugerencia: " + str(e)}), 500

    finally:
        cur.close()
        conn.close()



@api_bp.route('/rechazar_sugerencia/<int:id_sugerencia>', methods=['POST'])
def rechazar_sugerencia(id_sugerencia):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Actualizar el estado de la sugerencia a 'rechazada'
        query = "UPDATE sugerencias SET estado = 'rechazada' WHERE id_sugerencia = %s"
        cur.execute(query, (id_sugerencia,))

        # Confirmar los cambios
        conn.commit()

        return jsonify({"message": "Sugerencia rechazada correctamente"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Error al rechazar sugerencia: " + str(e)}), 500

    finally:
        cur.close()
        conn.close()

