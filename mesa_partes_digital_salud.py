import os
import re
from datetime import datetime

ARCHIVO = "solicitudes_salud.txt"

TIPOS_SOLICITUD = [
    "Atención médica",
    "Medicamentos",
    "Ambulancia",
    "Ayuda a establecimiento de salud",
]

URGENCIAS = ["Inmediata", "Urgente", "Programable", "No determinada"]

# Orden explícito para presentar primero lo crítico y lo que exige revisión humana.
ORDEN_PRIORIDAD = {
    "CRITICA": 0,
    "ALTA": 1,
    "PENDIENTE DE REVISION": 2,
    "MEDIA": 3,
    "BAJA": 4,
}

PUNTAJE_URGENCIA = {
    "Inmediata": 5,
    "Urgente": 3,
    "Programable": 1,
}

PUNTAJE_TIPO = {
    "Atención médica": 2,
    "Medicamentos": 1,
    "Ambulancia": 2,
    "Ayuda a establecimiento de salud": 1,
}

CAMPOS_ARCHIVO = 10


def validar_texto(mensaje):
    """Solicita texto obligatorio y rechaza delimitadores o saltos de línea."""
    while True:
        texto = input(mensaje).strip()
        if not texto:
            print("El campo es obligatorio. Inténtalo nuevamente.")
        elif "|" in texto or "\n" in texto or "\r" in texto:
            print("No uses el carácter | ni saltos de línea en este campo.")
        else:
            return texto


def leer_opcion(mensaje, cantidad_opciones):
    """Lee un número de menú válido, repitiendo la solicitud si hay errores."""
    while True:
        valor = input(mensaje).strip()
        try:
            opcion = int(valor)
            if 1 <= opcion <= cantidad_opciones:
                return opcion
            print(f"Selecciona una opción del 1 al {cantidad_opciones}.")
        except ValueError:
            print("Entrada incorrecta: escribe un número entero.")


def leer_afectados():
    """Acepta una cantidad opcional no negativa; vacío significa dato no informado."""
    while True:
        valor = input("Personas afectadas (número, o Enter si no se conoce): ").strip()
        if valor == "":
            return None
        try:
            cantidad = int(valor)
            if cantidad < 0:
                print("La cantidad no puede ser negativa.")
            else:
                return cantidad
        except ValueError:
            print("Ingresa un número entero no negativo o deja el campo vacío.")


def generar_codigo():
    """Busca el mayor código existente en el archivo, incluso en líneas dañadas."""
    mayor = 0
    if not os.path.exists(ARCHIVO):
        return "SOL" + str(1).zfill(4)

    try:
        with open(ARCHIVO, "r", encoding="utf-8") as archivo:
            for linea in archivo:
                primer_campo = linea.rstrip("\n\r").split("|", 1)[0].strip()
                coincidencia = re.fullmatch(r"SOL(\d+)", primer_campo)
                if coincidencia:
                    mayor = max(mayor, int(coincidencia.group(1)))
    except (OSError, UnicodeError) as error:
        print("No se pudo revisar el archivo para generar el código:", error)
        return None

    return "SOL" + str(mayor + 1).zfill(4)


def cargar_solicitudes():
    """Carga registros válidos; omite líneas dañadas y las informa sin detenerse."""
    solicitudes = []
    if not os.path.exists(ARCHIVO):
        return solicitudes

    lineas_danadas = 0
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as archivo:
            for numero_linea, linea in enumerate(archivo, start=1):
                if not linea.strip():
                    continue
                datos = linea.rstrip("\n\r").split("|")
                if len(datos) != CAMPOS_ARCHIVO:
                    lineas_danadas += 1
                    continue

                (codigo, tipo, solicitante, ubicacion, descripcion, afectados,
                 urgencia, prioridad, fecha, motivo) = datos

                if (not re.fullmatch(r"SOL\d+", codigo)
                        or tipo not in TIPOS_SOLICITUD
                        or urgencia not in URGENCIAS
                        or prioridad not in ORDEN_PRIORIDAD):
                    lineas_danadas += 1
                    continue

                if afectados == "":
                    numero_afectados = None
                elif afectados.isdigit():
                    numero_afectados = int(afectados)
                else:
                    lineas_danadas += 1
                    continue

                try:
                    datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    lineas_danadas += 1
                    continue

                solicitudes.append({
                    "codigo": codigo,
                    "tipo": tipo,
                    "solicitante": solicitante,
                    "ubicacion": ubicacion,
                    "descripcion": descripcion,
                    "afectados": numero_afectados,
                    "urgencia": urgencia,
                    "prioridad": prioridad,
                    "fecha": fecha,
                    "motivo": motivo,
                })
    except (OSError, UnicodeError) as error:
        print("No se pudo leer el archivo de solicitudes:", error)
        return solicitudes

    if lineas_danadas:
        print(f"Aviso: se omitieron {lineas_danadas} línea(s) dañada(s) del archivo.")
    return solicitudes


def clasificar_prioridad(tipo, urgencia, afectados):
    """Devuelve (nivel, puntaje, explicación) usando reglas no clínicas."""
    if urgencia == "No determinada":
        motivo = (
            "La urgencia no está determinada; requiere revisión humana antes "
            "de decidir el orden de atención."
        )
        return "PENDIENTE DE REVISION", None, motivo

    puntaje_urgencia = PUNTAJE_URGENCIA[urgencia]
    puntaje_tipo = PUNTAJE_TIPO[tipo]
    puntaje_afectados = 0
    partes = [
        f"urgencia declarada {urgencia} (+{puntaje_urgencia})",
        f"tipo de solicitud (+{puntaje_tipo})",
    ]

    if afectados is not None and afectados >= 10:
        puntaje_afectados = 2
        partes.append("10 o más personas afectadas (+2)")
    elif afectados is not None and afectados >= 4:
        puntaje_afectados = 1
        partes.append("entre 4 y 9 personas afectadas (+1)")
    elif afectados is None:
        partes.append("cantidad de personas no informada (+0)")

    puntaje = puntaje_urgencia + puntaje_tipo + puntaje_afectados
    if puntaje >= 7:
        prioridad = "CRITICA"
    elif puntaje >= 5:
        prioridad = "ALTA"
    elif puntaje >= 3:
        prioridad = "MEDIA"
    else:
        prioridad = "BAJA"

    motivo = f"Puntaje {puntaje}: " + "; ".join(partes) + "."
    return prioridad, puntaje, motivo


def guardar_solicitudes(solicitud):
    """Anexa un registro al TXT; no reescribe ni elimina líneas previas dañadas."""
    campos = [
        solicitud["codigo"],
        solicitud["tipo"],
        solicitud["solicitante"],
        solicitud["ubicacion"],
        solicitud["descripcion"],
        "" if solicitud["afectados"] is None else str(solicitud["afectados"]),
        solicitud["urgencia"],
        solicitud["prioridad"],
        solicitud["fecha"],
        solicitud["motivo"],
    ]

    if any("|" in campo or "\n" in campo or "\r" in campo for campo in campos):
        print("No se guardó la solicitud: hay caracteres que alteran el formato del archivo.")
        return False

    try:
        with open(ARCHIVO, "a", encoding="utf-8") as archivo:
            archivo.write("|".join(campos) + "\n")
        return True
    except (OSError, UnicodeError) as error:
        print("No se pudo guardar la solicitud:", error)
        return False


def mostrar_solicitud(solicitud):
    """Muestra los datos principales y la razón de clasificación."""
    afectados = (
        "No informado" if solicitud["afectados"] is None
        else str(solicitud["afectados"])
    )
    print("-" * 62)
    print("Código:", solicitud["codigo"])
    print("Tipo:", solicitud["tipo"])
    print("Solicitante:", solicitud["solicitante"])
    print("Ubicación:", solicitud["ubicacion"])
    print("Descripción:", solicitud["descripcion"])
    print("Personas afectadas:", afectados)
    print("Urgencia declarada:", solicitud["urgencia"])
    print("Prioridad administrativa:", solicitud["prioridad"])
    print("Fecha de registro:", solicitud["fecha"])
    print("Criterio aplicado:", solicitud["motivo"])


def registrar_solicitud(solicitudes):
    """Recoge, valida, clasifica y guarda una solicitud sanitaria."""
    print("\n--- REGISTRAR SOLICITUD SANITARIA ---")
    print("Usa datos ficticios en esta versión académica; no registres historias clínicas.")

    print("\nTipos de solicitud:")
    for indice, tipo in enumerate(TIPOS_SOLICITUD, start=1):
        print(f"{indice}. {tipo}")
    tipo = TIPOS_SOLICITUD[leer_opcion("Selecciona el tipo (1-4): ", len(TIPOS_SOLICITUD)) - 1]

    solicitante = validar_texto("Nombre o referencia del solicitante: ")
    ubicacion = validar_texto("Ubicación o establecimiento relacionado: ")
    descripcion = validar_texto("Descripción breve de la necesidad: ")
    afectados = leer_afectados()

    print("\nUrgencia declarada (no equivale a valoración clínica):")
    for indice, urgencia_opcion in enumerate(URGENCIAS, start=1):
        print(f"{indice}. {urgencia_opcion}")
    urgencia = URGENCIAS[leer_opcion("Selecciona la urgencia (1-4): ", len(URGENCIAS)) - 1]

    prioridad, puntaje, motivo = clasificar_prioridad(tipo, urgencia, afectados)
    codigo = generar_codigo()
    if codigo is None:
        print("La solicitud no se registró porque no fue posible generar un código.")
        return

    solicitud = {
        "codigo": codigo,
        "tipo": tipo,
        "solicitante": solicitante,
        "ubicacion": ubicacion,
        "descripcion": descripcion,
        "afectados": afectados,
        "urgencia": urgencia,
        "prioridad": prioridad,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "motivo": motivo,
    }

    if guardar_solicitudes(solicitud):
        solicitudes.append(solicitud)
        print("\nSolicitud registrada correctamente.")
        print("Código asignado:", codigo)
        print("Prioridad administrativa:", prioridad)
        print("Criterio:", motivo)
        if prioridad == "PENDIENTE DE REVISION":
            print("Atención: una persona responsable debe revisar la urgencia.")
    else:
        print("No se confirmó el registro porque el archivo no pudo guardarse.")


def buscar_solicitud(solicitudes):
    """Busca por código sin distinguir mayúsculas y minúsculas."""
    print("\n--- BUSCAR SOLICITUD ---")
    codigo = input("Ingresa el código (por ejemplo, SOL0001): ").strip().upper()
    if not codigo:
        print("Debes ingresar un código.")
        return

    for solicitud in solicitudes:
        if solicitud["codigo"].upper() == codigo:
            mostrar_solicitud(solicitud)
            return
    print("No se encontró una solicitud con ese código.")


def listar_solicitudes_ordenadas(solicitudes):
    """Ordena por prioridad definida y, en empate, por fecha de registro ascendente."""
    print("\n--- SOLICITUDES ORDENADAS POR PRIORIDAD ---")
    if not solicitudes:
        print("No hay solicitudes registradas.")
        return

    ordenadas = sorted(
        solicitudes,
        key=lambda solicitud: (
            ORDEN_PRIORIDAD.get(solicitud["prioridad"], 99),
            solicitud["fecha"],
        ),
    )
    for solicitud in ordenadas:
        mostrar_solicitud(solicitud)
    print("Total de solicitudes:", len(ordenadas))


def mostrar_estadisticas(solicitudes):
    """Muestra el total y un conteo simple por tipo y prioridad."""
    print("\n--- RESUMEN DE SOLICITUDES ---")
    print("Total de solicitudes registradas:", len(solicitudes))
    print("\nPor tipo:")
    for tipo in TIPOS_SOLICITUD:
        cantidad = sum(1 for solicitud in solicitudes if solicitud["tipo"] == tipo)
        print(f"- {tipo}: {cantidad}")

    print("\nPor prioridad administrativa:")
    for prioridad in ["CRITICA", "ALTA", "PENDIENTE DE REVISION", "MEDIA", "BAJA"]:
        cantidad = sum(
            1 for solicitud in solicitudes if solicitud["prioridad"] == prioridad
        )
        print(f"- {prioridad}: {cantidad}")


def menu_principal():
    """Carga datos y mantiene activo el menú hasta seleccionar Salir."""
    solicitudes = cargar_solicitudes()
    print("Mesa de Partes Digital-Salud | Prototipo educativo")
    if not os.path.exists(ARCHIVO):
        print("Archivo de datos aún no creado; se generará al guardar la primera solicitud.")
    elif solicitudes:
        print("Solicitudes válidas cargadas:", len(solicitudes))

    while True:
        print("\n" + "=" * 48)
        print(" MESA DE PARTES DIGITAL-SALUD")
        print("=" * 48)
        print("1. Registrar solicitud")
        print("2. Buscar solicitud por código")
        print("3. Listar solicitudes ordenadas")
        print("4. Mostrar estadísticas")
        print("5. Salir")
        opcion = leer_opcion("Selecciona una opción (1-5): ", 5)

        if opcion == 1:
            registrar_solicitud(solicitudes)
        elif opcion == 2:
            buscar_solicitud(solicitudes)
        elif opcion == 3:
            listar_solicitudes_ordenadas(solicitudes)
        elif opcion == 4:
            mostrar_estadisticas(solicitudes)
        elif opcion == 5:
            print("Programa finalizado. Los registros guardados permanecen en el archivo TXT.")
            break


if __name__ == "__main__":
    menu_principal()
