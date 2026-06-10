from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty
from kivy.lang import Builder
from datetime import datetime
import sqlite3
import os


# ---------------- BASE DE DATOS ----------------
# Ruta compatible con Android (almacenamiento interno de la app)
def get_db_path():
    from kivy.utils import platform
    if platform == "android":
        from android.storage import app_storage_path  # type: ignore
        return os.path.join(app_storage_path(), "ujat_horarios.db")
    return "ujat_horarios.db"


def get_connection():
    """Crea una nueva conexión (seguro para Android/hilos)."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        nombre TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS administradores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id TEXT UNIQUE,
        nombre TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profesor_id TEXT,
        profesor_nombre TEXT,
        dia TEXT,
        hora_entrada TEXT,
        hora_salida TEXT
    )""")

    # Datos iniciales
    c.execute("INSERT OR IGNORE INTO administradores (admin_id, nombre) VALUES (?, ?)",
              ("ADMIN001", "Administrador"))

    profesores_iniciales = [
        ("E4C56G789", "EDUARDO CRUCES GUTIERREZ"),
        ("M2T78F546", "MARÍA TERESA FERNÁNDEZ MENA"),
        ("C6G56Z098", "CARLOS GONZÁLEZ ZACARÍAS"),
    ]
    for uid, nombre in profesores_iniciales:
        c.execute("INSERT OR IGNORE INTO usuarios (usuario, nombre) VALUES (?, ?)", (uid, nombre))

    conn.commit()
    conn.close()


# ---------------- PANTALLAS ----------------

class InicioScreen(Screen):
    pass


class LoginAdminScreen(Screen):

    def validar_admin(self):
        admin_id = self.ids.admin_input.text.strip()
        self.ids.error_label.text = ""

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT nombre FROM administradores WHERE admin_id=?", (admin_id,))
        r = c.fetchone()
        conn.close()

        if r:
            self.manager.current = "menu_admin"
            self.ids.admin_input.text = ""
        else:
            self.ids.admin_input.text = ""
            self.ids.error_label.text = "ID de administrador no válido"


class LoginScreen(Screen):

    def validar_usuario(self):
        profesor_id = self.ids.id_input.text.strip()
        self.ids.error_label.text = ""

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT nombre FROM usuarios WHERE usuario=?", (profesor_id,))
        r = c.fetchone()
        conn.close()

        if r:
            self.manager.profesor_actual = {"id": profesor_id, "nombre": r[0]}
            self.ids.id_input.text = ""
            self.manager.current = "menu"
        else:
            self.ids.id_input.text = ""
            self.ids.error_label.text = "ID no encontrado. Verifica tu clave."


class MenuScreen(Screen):

    def on_enter(self):
        """Muestra el nombre del profesor al entrar al menú."""
        profesor = self.manager.profesor_actual
        if profesor:
            self.ids.bienvenido_label.text = f"Bienvenido, {profesor['nombre']}"
            self.ids.id_label.text = f"Clave: {profesor['id']}"


class RegistroScreen(Screen):
    registro = StringProperty("")

    def on_enter(self):
        profesor = self.manager.profesor_actual
        if profesor:
            self.ids.profesor_label.text = f"{profesor['nombre']}  ·  {profesor['id']}"

    def get_profesor(self):
        return self.manager.profesor_actual

    def registrar_entrada(self):
        profesor = self.get_profesor()
        if not profesor:
            self.registro = "⚠ Sin sesión activa"
            return

        dia = self.ids.dia_spinner.text
        if dia == "Selecciona un día":
            self.registro = "⚠ Elige el día primero"
            return

        ahora = datetime.now()
        fecha_hora = ahora.strftime("%Y-%m-%d %H:%M:%S")
        hora_str = ahora.strftime("%I:%M %p")

        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT 1 FROM registros
            WHERE profesor_id=? AND dia=? AND hora_salida='Pendiente'
        """, (profesor["id"], dia))
        existe = c.fetchone()

        if existe:
            conn.close()
            self.registro = f"⚠ Ya tienes entrada abierta el {dia}"
            return

        c.execute("""
            INSERT INTO registros VALUES (NULL,?,?,?,?,?)
        """, (profesor["id"], profesor["nombre"], dia, fecha_hora, "Pendiente"))
        conn.commit()
        conn.close()
        self.registro = f"✓ Entrada registrada — {dia} {hora_str}"

    def registrar_salida(self):
        profesor = self.get_profesor()
        if not profesor:
            self.registro = "⚠ Sin sesión activa"
            return

        ahora = datetime.now()
        fecha_hora = ahora.strftime("%Y-%m-%d %H:%M:%S")
        hora_str = ahora.strftime("%I:%M %p")

        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, dia FROM registros
            WHERE profesor_id=? AND hora_salida='Pendiente'
            ORDER BY id DESC LIMIT 1
        """, (profesor["id"],))
        r = c.fetchone()

        if not r:
            conn.close()
            self.registro = "⚠ No hay entrada abierta"
            return

        c.execute("UPDATE registros SET hora_salida=? WHERE id=?", (fecha_hora, r[0]))
        conn.commit()
        conn.close()
        self.registro = f"✓ Salida registrada — {r[1]} {hora_str}"


# ---------------- ADMIN ----------------

class MenuAdminScreen(Screen):

    def cargar_profesores(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT usuario, nombre FROM usuarios ORDER BY nombre")
        data = c.fetchall()
        conn.close()

        if not data:
            self.ids.output.text = "Sin profesores registrados."
            return

        self.ids.output.text = "\n".join([f"• {r[1]}\n  Clave: {r[0]}" for r in data])

    def cargar_registros(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT profesor_nombre, dia, hora_entrada, hora_salida
            FROM registros ORDER BY id DESC
        """)
        data = c.fetchall()
        conn.close()

        if not data:
            self.ids.output.text = "Sin registros aún."
            return

        lineas = []
        for nombre, dia, entrada, salida_sql in data:
            fecha = "N/A"
            hora_in = "N/A"
            hora_out = "Pendiente ⏳"

            if entrada and " " in entrada:
                fecha_raw, hora_raw = entrada.split(" ", 1)
                try:
                    fecha = datetime.strptime(fecha_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
                    hora_in = datetime.strptime(hora_raw, "%H:%M:%S").strftime("%I:%M %p")
                except ValueError:
                    pass

            if salida_sql and salida_sql != "Pendiente" and " " in salida_sql:
                try:
                    hora_out = datetime.strptime(
                        salida_sql.split(" ")[1], "%H:%M:%S"
                    ).strftime("%I:%M %p")
                except ValueError:
                    pass

            lineas.append(
                f"──────────────────\n"
                f"👤 {nombre}\n"
                f"📅 {dia}  —  {fecha}\n"
                f"🟢 Entrada: {hora_in}\n"
                f"🔴 Salida:  {hora_out}\n"
            )

        self.ids.output.text = "\n".join(lineas)

    def agregar_profesor(self):
        uid = self.ids.new_id.text.strip().upper()
        nombre = self.ids.new_name.text.strip()
        self.ids.admin_msg.text = ""

        if not uid or not nombre:
            self.ids.admin_msg.text = "⚠ Completa ID y nombre"
            return

        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT OR IGNORE INTO usuarios VALUES (NULL,?,?)", (uid, nombre))
            conn.commit()
            self.ids.admin_msg.text = f"✓ Profesor '{nombre}' agregado"
        except Exception as e:
            self.ids.admin_msg.text = f"Error: {e}"
        finally:
            conn.close()

        self.ids.new_id.text = ""
        self.ids.new_name.text = ""

    def eliminar_profesor(self):
        uid = self.ids.new_id.text.strip().upper()
        if not uid:
            self.ids.admin_msg.text = "⚠ Ingresa el ID a eliminar"
            return

        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM usuarios WHERE usuario=?", (uid,))
        cambios = conn.total_changes
        conn.commit()
        conn.close()

        if cambios:
            self.ids.admin_msg.text = f"✓ Profesor {uid} eliminado"
        else:
            self.ids.admin_msg.text = f"⚠ No se encontró el ID {uid}"

        self.ids.new_id.text = ""


class WindowManager(ScreenManager):
    profesor_actual = None


class MiApp(App):
    def build(self):
        init_db()
        return Builder.load_file("miapp.kv")


if __name__ == "__main__":
    MiApp().run()
