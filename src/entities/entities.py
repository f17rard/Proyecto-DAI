from value_objects.value_objects import ServicioContratado, ServicioPersonalExtra


class Empleado:
    """
    Empleado responsable de una Orden_Servicio.

    Este objeto NUNCA se crea de forma independiente y luego se "engancha" a
    la orden: se instancia obligatoriamente dentro del constructor de
    OrdenServicio (Composicion pura).
    """

    def __init__(self, nombre_completo: str, cargo: str,
                 email: str = "", telefono: str = ""):
        self.nombre_completo = nombre_completo
        self.cargo = cargo  # "Coordinador", "AUX-Logistica", etc.
        self.email = email
        self.telefono = telefono

    def es_personal_auxiliar(self) -> bool:
        return self.cargo.upper().startswith("AUX")

    def __repr__(self):
        return f"Empleado({self.nombre_completo}, cargo={self.cargo})"


class OrdenServicio:
    """
    Entidad CONDUCTORA del sistema.

    Invariante de negocio: una OrdenServicio no puede existir sin un
    Empleado responsable. Por eso el Empleado se crea DENTRO del
    constructor, nunca se recibe como objeto ya armado desde afuera.
    """

    MAX_SERVICIOS_POR_ORDEN = 4

    def __init__(self, orden_id: int, evento_id_fk: int,
                 nombre_empleado: str, cargo_empleado: str,
                 monto_total: float = 0.0):
        self.orden_id = orden_id
        self.evento_id_fk = evento_id_fk
        self.monto_total = monto_total
        self.estado = "PENDIENTE"

        self._responsable = Empleado(nombre_empleado, cargo_empleado)

        self._servicios_contratados = []

    @property
    def responsable(self) -> Empleado:
        return self._responsable

    @property
    def servicios_contratados(self):
        """
        Encapsulamiento defensivo: entrega la lista como una TUPLA
        (coleccion congelada/inmutable). Si algo externo intenta hacer
        .append() o .clear() sobre lo que retorna esta propiedad, Python
        arrojara un AttributeError de inmediato porque las tuplas no
        soportan esos metodos.
        """
        return tuple(self._servicios_contratados)

    def cargar_servicio(self, servicio: ServicioContratado) -> None:
        if self.estado == "CUENTA_SUSPENDIDA":
            raise RuntimeError(
                "No se pueden cargar servicios: la orden esta suspendida."
            )
        if len(self._servicios_contratados) >= self.MAX_SERVICIOS_POR_ORDEN:
            raise ValueError("Limite de servicios por orden alcanzado")
        self._servicios_contratados.append(servicio)

    def calcular_recargos_totales(self) -> float:
        """
        Ordena a TODOS los servicios cargados calcular su recargo
        simultaneamente, sin saber de que tipo especifico es cada uno.
        Este es el punto exacto de Polimorfismo puro.
        """
        return sum(s.calcular_recargo() for s in self._servicios_contratados)

    def generarOrden(self) -> None:
        if self.estado == "CUENTA_SUSPENDIDA":
            raise RuntimeError("No se puede generar la orden: cuenta suspendida.")
        print(f"Orden {self.orden_id} generada correctamente. "
              f"Responsable: {self._responsable.nombre_completo}")

    def procesarPago(self) -> bool:
        if self.estado == "CUENTA_SUSPENDIDA":
            raise RuntimeError("No se puede procesar el pago: cuenta suspendida.")
        print(f"Pago de la orden {self.orden_id} procesado por "
              f"${self.monto_total:.2f}")
        return True

# ==============================================================================
# COMMIT 2 - EVOLUCION DEL DOMINIO (nueva regla de negocio)
# ==============================================================================
#
# "Si al finalizar una revision de recargos, el PROMEDIO de recargos de
# todos los servicios contratados en la orden supera los $15.00, O si el
# empleado responsable es Personal Auxiliar (cargo inicia con 'AUX') Y la
# orden tiene un ServicioPersonalExtra con mas de 10 ordenes en espera,
# el sistema debe activar automaticamente un protocolo de restriccion,
# cambiando el estado de la orden a 'CUENTA_SUSPENDIDA'."
#
# Esta regla vive aqui (en entities.py, junto a OrdenServicio) porque
# depende de la RELACION entre varios servicios y del empleado responsable,
# nunca de un solo servicio individual. Por eso NO puede vivir dentro de
# ServicioMenu ni de ServicioPersonalExtra.
# ==============================================================================

def revisar_y_aplicar_restriccion(orden: OrdenServicio) -> None:
    """
    Ejecuta la revision de saldos de una OrdenServicio y aplica el
    protocolo de restriccion si corresponde.
    """
    servicios = orden.servicios_contratados  # tupla inmutable

    if not servicios:
        return

    total_recargos = sum(s.calcular_recargo() for s in servicios)
    promedio_recargos = total_recargos / len(servicios)

    condicion_promedio = promedio_recargos > 15.00

    empleado_es_aux = orden.responsable.es_personal_auxiliar()
    hay_personal_extra_criticos = any(
        isinstance(s, ServicioPersonalExtra) and s.ordenes_en_espera > 10
        for s in servicios
    )
    condicion_aux = empleado_es_aux and hay_personal_extra_criticos

    if condicion_promedio or condicion_aux:
        orden.estado = "CUENTA_SUSPENDIDA"
        print(f"[ALERTA] Orden {orden.orden_id} -> estado cambiado a "
              f"'CUENTA_SUSPENDIDA' (promedio_recargos=${promedio_recargos:.2f})")
    else:
        print(f"Orden {orden.orden_id} dentro de parametros normales "
              f"(promedio_recargos=${promedio_recargos:.2f})")
