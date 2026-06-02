from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty
from datetime import datetime
import sqlite3

# ---------------- BASE DE DATOS ----------------

conexion = sqlite3.connect("ujat_horarios.db")
cursor = conexion.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS profesores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matricula TEXT UNIQUE,
    nombre TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profesor_id INTEGER,
    profesor_nombre TEXT,
    fecha TEXT,
    dia TEXT,
    hora_entrada TEXT,
    hora_salida TEXT
)
""")

conexion.commit()

# Profesores de ejemplo
profesores = [
    ("E4C56G789", "Juan Pérez"),
    ("A2C78F546", "María López"),
    ("M6E56M098", "Carlos Ramírez")
]

for matricula, nombre in profesores:
    cursor.execute("""
    INSERT OR IGNORE INTO profesores (matricula, nombre)
    VALUES (?, ?)
    """, (matricula, nombre))

conexion.commit()

# ---------------- PANTALLAS ----------------

class LoginScreen(Screen):

    def validar_usuario(self):

        matricula = self.ids.matricula_input.text.strip()

        cursor.execute("""
        SELECT id, nombre FROM profesores
        WHERE matricula = ?
        """, (matricula,))

        resultado = cursor.fetchone()

        if resultado:
            self.manager.profesor_actual = resultado

            # actualizar label cuando entre
            self.manager.get_screen("registro").ids.bienvenida_label.text = \
                f"Bienvenido: {resultado[1]}"

            self.manager.current = "registro"


class RegistroScreen(Screen):

    registro = StringProperty("")

    def registrar_entrada(self):

        profesor = self.manager.profesor_actual

        if not profesor:
            self.registro = "No hay sesión activa"
            return

        profesor_id, nombre = profesor

        fecha = datetime.now().strftime("%Y-%m-%d")
        hora = datetime.now().strftime("%H:%M:%S")
        dia = self.ids.dia_spinner.text

        if dia == "Selecciona un día":
            self.registro = "Selecciona un día válido"
            return

        cursor.execute("""
        INSERT INTO registros
        (profesor_id, profesor_nombre, fecha, dia, hora_entrada, hora_salida)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (profesor_id, nombre, fecha, dia, hora, "Pendiente"))

        conexion.commit()

        self.registro = (
            f"Registro de entrada completado\n"
            f"Profesor: {nombre}\n"
            f"Fecha: {fecha}\n"
            f"Hora de entrada: {hora}"
)
        

    def registrar_salida(self):

        profesor = self.manager.profesor_actual

        if not profesor:
            self.registro = "No hay sesión activa"
            return

        profesor_id, nombre = profesor

        fecha = datetime.now().strftime("%Y-%m-%d")
        hora = datetime.now().strftime("%H:%M:%S")

        cursor.execute("""
        UPDATE registros
        SET hora_salida = ?
        WHERE profesor_id = ?
        AND fecha = ?
        AND hora_salida = 'Pendiente'
        """, (hora, profesor_id, fecha))

        conexion.commit()

        self.registro = (
            f"Registro de salida completado\n"
            f"Profesor: {nombre}\n"
            f"Fecha: {fecha}\n"
            f"Hora de salida: {hora}"
)
        


class WindowManager(ScreenManager):
    profesor_actual = None


class MiApp(App):
    pass


if __name__ == "__main__":
    MiApp().run()