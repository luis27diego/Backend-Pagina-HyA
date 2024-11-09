from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps
from models.db import get_db_connection
from models.get_usuarios_por_id import get_usuario_por_id   # Función para conectar a la base de datos
from config import Config
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__)

# Función decoradora para verificar el token JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-tokens')
        if not token:
            return jsonify({'error': 'Token es requerido'}), 403
        try:
            # Decodifica el token
            data = jwt.decode(token, Config.secret_key, algorithms=['HS256'])
            current_user = get_usuario_por_id(data['id_usuario'])
            if current_user is None:
                return jsonify({'error': 'Usuario no encontrado'}), 403
            # Verifica si el usuario es admin
            if current_user['rol'] != 'admin':  # Asegúrate de que current_user tenga el rol
                return jsonify({'error': 'Acceso denegado. Se requiere rol de admin.'}), 403

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token ha expirado'}), 403
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 403

        return f(current_user, *args, **kwargs)
    return decorated




@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    nombre = data.get('nombre')
    email = data.get('email')
    contraseña = data.get('contraseña')
    rol = data.get('rol', 'usuario')  # Por defecto, los usuarios no son administradores

    if not nombre or not email or not contraseña:
        return jsonify({'error': 'Faltan datos'}), 400

    # Hash de la contraseña
    contraseña_hashed = generate_password_hash(contraseña)

    # Conectar a la base de datos
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Insertar el nuevo usuario
        cur.execute("""
            INSERT INTO usuarios (nombre, email, contraseña, rol) 
            VALUES (%s, %s, %s, %s)
        """, (nombre, email, contraseña_hashed, rol))
        conn.commit()

        return jsonify({'message': 'Usuario registrado exitosamente'}), 201

    except Exception as e:
        print(f"Error al registrar usuario: {e}")
        return jsonify({"error": "Error al registrar usuario"}), 500

    finally:
        cur.close()
        conn.close()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    contraseña = data.get('contraseña')

    if not email or not contraseña:
        return jsonify({'error': 'Faltan datos'}), 400

    # Conectar a la base de datos
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Buscar al usuario por email
        cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        user = cur.fetchone()

        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        # Verificar la contraseña
        user_id = user[0]
        contraseña_hashed = user[3]  # Asumiendo que el campo de contraseña está en la tercera posición
        rol = user[4]  # Asumiendo que el campo de rol está en la cuarta posición

        if not check_password_hash(contraseña_hashed, contraseña):
            return jsonify({'error': 'Contraseña incorrecta'}), 401

        # Generar el token JWT
        token = jwt.encode({
            'id_usuario': user_id,
            'rol': rol,
            'exp': datetime.utcnow() + timedelta(hours=24)  # Token válido por 24 horas
        }, Config.secret_key, algorithm='HS256')

        return jsonify({'token': token, 'rol': rol}), 200  # Incluye el rol en la respuesta

    except Exception as e:
        print(f"Error al iniciar sesión: {e}")
        return jsonify({"error": "Error al iniciar sesión"}), 500

    finally:
        cur.close()
        conn.close()


@auth_bp.route('/usuarios/<int:user_id>', methods=['GET'])
def obtener_usuario(user_id):
    return get_usuario_por_id(user_id)