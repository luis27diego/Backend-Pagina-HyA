from .db import get_db_connection

def get_usuario_por_id(user_id):
    # Conectar a la base de datos
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Consultar la base de datos para obtener el usuario por ID
        cur.execute("SELECT * FROM usuarios WHERE id_usuario = %s", (user_id,))
        usuario = cur.fetchone()
        
        if usuario is None:
            return None  # Retorna None si no se encuentra el usuario

        # Retornar un diccionario con los datos del usuario
        return {
            'id_usuario': usuario[0],
            'nombre': usuario[1],
            'email': usuario[2],
            'rol': usuario[4]  # Suponiendo que el rol está en la cuarta posición
        }
    except Exception as e:
        print(f"Error al obtener el usuario: {e}")
        return None  # Puedes manejar el error de otra forma si lo prefieres
    finally:
        cur.close()
        conn.close()
