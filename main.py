from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty
from kivy.lang import Builder
from datetime import datetime
import sqlite3


# ---------------- BASE DE DATOS ----------------
conexion = sqlite3.connect("ujat_horarios.db")
cursor = conexion.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    nombre TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS administradores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id TEXT UNIQUE,
    nombre TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profesor_id TEXT,
    profesor_nombre TEXT,
    dia TEXT,
    hora_entrada TEXT,
    hora_salida TEXT
)
""")

conexion.commit()


# ---------------- DATOS ----------------
usuarios = [
    ("E4C56G789", "Carlos Pérez"),
    ("A2C78F546", "María López"),
    ("M6E56M098", "Juan Hernández")
]

cursor.execute("""
INSERT OR IGNORE INTO administradores (admin_id, nombre)
VALUES (?, ?)
""", ("ADMIN001", "Administrador"))

conexion.commit()

for u in usuarios:
    cursor.execute("""
    INSERT OR IGNORE INTO usuarios (usuario, nombre)
    VALUES (?, ?)
    """, u)

conexion.commit()


# ---------------- PANTALLAS ----------------

class InicioScreen(Screen):
    pass


class LoginAdminScreen(Screen):

    def validar_admin(self):
        admin_id = self.ids.admin_input.text.strip()

        cursor.execute("SELECT nombre FROM administradores WHERE admin_id=?", (admin_id,))
        r = cursor.fetchone()

        if r:
            self.manager.current = "menu_admin"
        else:
            self.ids.admin_input.text = ""


class LoginScreen(Screen):

    def validar_usuario(self):
        profesor_id = self.ids.id_input.text.strip()

        cursor.execute("SELECT nombre FROM usuarios WHERE usuario=?", (profesor_id,))
        r = cursor.fetchone()

        if r:
            self.manager.profesor_actual = {"id": profesor_id, "nombre": r[0]}
            self.manager.current = "menu"
        else:
            self.ids.id_input.text = ""


class MenuScreen(Screen):
    pass


class RegistroScreen(Screen):
    registro = StringProperty("")

    def get_profesor(self):
        return self.manager.profesor_actual

    def registrar_entrada(self):
        profesor = self.get_profesor()
        dia = self.ids.dia_spinner.text
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not profesor:
            self.registro = "Sin sesión"
            return

        cursor.execute("""
        SELECT 1 FROM registros
        WHERE profesor_id=? AND dia=? AND hora_salida='Pendiente'
        """, (profesor["id"], dia))

        if cursor.fetchone():
            self.registro = "Ya registrado"
            return

        cursor.execute("""
        INSERT INTO registros VALUES (NULL,?,?,?,?,?)
        """, (profesor["id"], profesor["nombre"], dia, fecha, "Pendiente"))

        conexion.commit()
        self.registro = "Entrada registrada"


    def registrar_salida(self):
        profesor = self.get_profesor()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        SELECT id FROM registros
        WHERE profesor_id=? AND hora_salida='Pendiente'
        ORDER BY id DESC LIMIT 1
        """, (profesor["id"],))

        r = cursor.fetchone()

        if not r:
            self.registro = "No hay entrada abierta"
            return

        cursor.execute("""
        UPDATE registros SET hora_salida=? WHERE id=?
        """, (fecha, r[0]))

        conexion.commit()
        self.registro = "Salida registrada"


# ---------------- ADMIN ----------------

class MenuAdminScreen(Screen):

    def cargar_profesores(self):
        cursor.execute("SELECT usuario, nombre FROM usuarios")
        data = cursor.fetchall()

        if not data:
            self.ids.output.text = "Sin profesores"
            return

        self.ids.output.text = "\n".join([f"{u} - {n}" for u, n in data])


    def cargar_registros(self):
        cursor.execute("""
        SELECT profesor_nombre, dia, hora_entrada, hora_salida
        FROM registros
        ORDER BY id DESC
        """)
        data = cursor.fetchall()

        salida = ""

        for nombre, dia, entrada, salida_sql in data:

            fecha = "N/A"
            hora_in = "N/A"
            hora_out = "Pendiente"

            if entrada and " " in entrada:
                fecha, hora_in = entrada.split(" ")

            if salida_sql and salida_sql != "Pendiente" and " " in salida_sql:
                hora_out = salida_sql.split(" ")[1]

            salida += (
                f"{nombre}\n"
                f"{dia}\n"
                f"Fecha: {fecha}\n"
                f"Entrada: {hora_in}\n"
                f"Salida: {hora_out}\n\n"
            )

        self.ids.output.text = salida


    def agregar_profesor(self):
        uid = self.ids.new_id.text.strip()
        nombre = self.ids.new_name.text.strip()

        if uid and nombre:
            cursor.execute("INSERT OR IGNORE INTO usuarios VALUES (NULL,?,?)", (uid, nombre))
            conexion.commit()

        self.ids.new_id.text = ""
        self.ids.new_name.text = ""


class WindowManager(ScreenManager):
    profesor_actual = None


class MiApp(App):
    def build(self):
        return Builder.load_file("miapp.kv")


if __name__ == "__main__":
    MiApp().run()