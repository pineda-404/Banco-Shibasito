#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor Yapesito - Banco Simple
Maneja operaciones básicas y transferencias interbancarias
"""

import json
import os
import sqlite3
import sys
import threading
import time
from datetime import datetime

import pika

# Path de la base de datos
DB_PATH = os.path.join(os.path.dirname(__file__), "db_yapesito.db")
YAPESITO_QUEUE = "yapesito_queue"


class ServidorYapesito:
    def __init__(self):
        self.db_path = DB_PATH
        self.db_lock = threading.Lock()
        self._init_rabbitmq()
        print(f"[Yapesito] Base de datos: {self.db_path}")

    def _init_rabbitmq(self):
        """Inicializa conexión a RabbitMQ con reintentos"""
        max_attempts = 5
        retry_delay = 3

        for attempt in range(1, max_attempts + 1):
            try:
                print(
                    f"[Yapesito] Intento {attempt}/{max_attempts} de conexión a RabbitMQ...",
                    flush=True,
                )
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host="localhost", connection_attempts=3, retry_delay=2
                    )
                )
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue=YAPESITO_QUEUE, durable=True)
                print("[Yapesito] ✓ Conectado exitosamente a RabbitMQ", flush=True)
                print(f"[Yapesito] ✓ Escuchando en cola '{YAPESITO_QUEUE}'", flush=True)
                return
            except Exception as e:
                print(f"[Yapesito] ✗ Error en intento {attempt}: {e}", flush=True)
                if attempt < max_attempts:
                    print(
                        f"[Yapesito] Reintentando en {retry_delay} segundos...",
                        flush=True,
                    )
                    time.sleep(retry_delay)
                else:
                    print(
                        f"[Yapesito] ✗ FALLO CRÍTICO: No se pudo conectar después de {max_attempts} intentos",
                        flush=True,
                    )
                    sys.exit(1)

    def on_message(self, ch, method, props, body):
        """Callback para mensajes entrantes"""
        try:
            message = body.decode("utf-8")
            print(f"[Yapesito] >>> Mensaje recibido: {message}")
            req = json.loads(message)
            req_type = req.get("type", "").upper()

            # Enrutar según tipo de operación
            if req_type == "LOGIN":
                response_data = self._handle_login(req)
            elif req_type == "CONSULTAR_CUENTA":
                response_data = self._handle_consultar_cuenta(req)
            elif req_type == "TRANSFERIR_CUENTA":
                response_data = self._handle_transferir(req)
            elif req_type == "CREDITO_INTERBANCARIO":
                response_data = self._handle_credito_interbancario(req)
            elif req_type == "CONSULTAR_HISTORIAL":
                response_data = self._handle_historial(req)
            elif req_type == "TRANSFERIR_INTERBANCARIA":
                response_data = self._handle_transferir_a_shibasito(req)
            else:
                response_data = {"status": "ERROR", "error": "TIPO_DESCONOCIDO"}

            # Enviar respuesta si hay reply_to
            if props.reply_to:
                ch.basic_publish(
                    exchange="",
                    routing_key=props.reply_to,
                    properties=pika.BasicProperties(
                        correlation_id=props.correlation_id
                    ),
                    body=json.dumps(response_data, default=str),
                )
                print(f"[Yapesito] <<< Respuesta: {response_data.get('status')}")

        except Exception as e:
            print(f"[Yapesito] [ERROR] {e}")
            import traceback
            traceback.print_exc()
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def _handle_login(self, req):
        """Maneja login de usuario"""
        dni = req.get("dni")
        cuenta = req.get("account")

        if not dni or not cuenta:
            return {"status": "ERROR", "error": "DNI y cuenta requeridos"}

        with self.db_lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM Cuentas WHERE id_cuenta = ? AND dni = ?",
                        (cuenta, dni)
                    )
                    cuenta_data = cursor.fetchone()

                    if cuenta_data:
                        return {
                            "status": "OK",
                            "account": cuenta_data["id_cuenta"],
                            "nombre": cuenta_data["nombre_cliente"],
                            "dni": cuenta_data["dni"],
                        }
                    else:
                        return {"status": "ERROR", "error": "Credenciales inválidas"}
            except Exception as e:
                print(f"[Yapesito] Error en login: {e}")
                return {"status": "ERROR", "error": str(e)}

    def _handle_consultar_cuenta(self, req):
        """Consulta saldo de una cuenta"""
        cuenta = req.get("account")

        if not cuenta:
            return {"status": "ERROR", "error": "Cuenta requerida"}

        with self.db_lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id_cuenta, saldo FROM Cuentas WHERE id_cuenta = ?",
                        (cuenta,)
                    )
                    row = cursor.fetchone()

                    if row:
                        return {
                            "status": "OK",
                            "account": row["id_cuenta"],
                            "balance": row["saldo"],
                        }
                    else:
                        return {"status": "ERROR", "error": "Cuenta no encontrada"}
            except Exception as e:
                print(f"[Yapesito] Error consultando cuenta: {e}")
                return {"status": "ERROR", "error": str(e)}

    def _handle_transferir(self, req):
        """Maneja transferencia entre cuentas Yapesito"""
        cuenta_origen = req.get("cuenta_origen")
        cuenta_destino = req.get("cuenta_destino")
        monto = req.get("monto")

        if not all([cuenta_origen, cuenta_destino, monto]):
            return {"status": "ERROR", "error": "Datos incompletos"}

        monto = float(monto)

        with self.db_lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("BEGIN TRANSACTION")
                    cursor = conn.cursor()

                    # Verificar saldo origen
                    cursor.execute(
                        "SELECT saldo FROM Cuentas WHERE id_cuenta = ?", (cuenta_origen,)
                    )
                    row = cursor.fetchone()
                    if not row or row[0] < monto:
                        conn.rollback()
                        return {"status": "ERROR", "error": "Saldo insuficiente"}

                    # Verificar cuenta destino existe
                    cursor.execute(
                        "SELECT id_cuenta FROM Cuentas WHERE id_cuenta = ?",
                        (cuenta_destino,)
                    )
                    if not cursor.fetchone():
                        conn.rollback()
                        return {"status": "ERROR", "error": "Cuenta destino no existe"}

                    # Debitar origen
                    cursor.execute(
                        "UPDATE Cuentas SET saldo = saldo - ? WHERE id_cuenta = ?",
                        (monto, cuenta_origen),
                    )
                    cursor.execute(
                        "INSERT INTO Transacciones (id_cuenta, tipo, monto, referencia) VALUES (?, ?, ?, ?)",
                        (cuenta_origen, "DEBITO", monto, f"Transferencia a {cuenta_destino}"),
                    )

                    # Acreditar destino
                    cursor.execute(
                        "UPDATE Cuentas SET saldo = saldo + ? WHERE id_cuenta = ?",
                        (monto, cuenta_destino),
                    )
                    cursor.execute(
                        "INSERT INTO Transacciones (id_cuenta, tipo, monto, referencia) VALUES (?, ?, ?, ?)",
                        (cuenta_destino, "CREDITO", monto, f"Transferencia desde {cuenta_origen}"),
                    )

                    conn.commit()
                    print(f"[Yapesito] ✓ Transferencia: {cuenta_origen} -> {cuenta_destino} S/ {monto}")
                    return {"status": "OK", "message": "Transferencia exitosa"}

            except Exception as e:
                print(f"[Yapesito] Error en transferencia: {e}")
                return {"status": "ERROR", "error": str(e)}

    def _handle_credito_interbancario(self, req):
        """Recibe crédito desde otro banco"""
        cuenta_destino = req.get("cuenta_destino")
        monto = req.get("monto")
        tx_id = req.get("tx_id")
        banco_origen = req.get("banco_origen", "DESCONOCIDO")

        if not all([cuenta_destino, monto]):
            return {"status": "ERROR", "error": "Datos incompletos"}

        monto = float(monto)

        with self.db_lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()

                    # Verificar cuenta existe
                    cursor.execute(
                        "SELECT id_cuenta FROM Cuentas WHERE id_cuenta = ?",
                        (cuenta_destino,)
                    )
                    if not cursor.fetchone():
                        return {"status": "ERROR", "error": "Cuenta no encontrada"}

                    # Acreditar
                    cursor.execute(
                        "UPDATE Cuentas SET saldo = saldo + ? WHERE id_cuenta = ?",
                        (monto, cuenta_destino),
                    )
                    cursor.execute(
                        "INSERT INTO Transacciones (id_cuenta, tipo, monto, referencia) VALUES (?, ?, ?, ?)",
                        (cuenta_destino, "CREDITO_INTERBANCARIO", monto, f"Desde {banco_origen} TX:{tx_id}"),
                    )

                    conn.commit()
                    print(f"[Yapesito] ✓ Crédito interbancario: {cuenta_destino} +S/ {monto} desde {banco_origen}")
                    return {"status": "OK", "message": "Crédito aplicado"}

            except Exception as e:
                print(f"[Yapesito] Error en crédito interbancario: {e}")
                return {"status": "ERROR", "error": str(e)}

    def _handle_transferir_a_shibasito(self, req):
        """Envía dinero desde Yapesito a Shibasito"""
        cuenta_origen = req.get("cuenta_origen")  # YAP-XXXX
        cuenta_destino = req.get("cuenta_destino")  # Número Shibasito
        monto = req.get("monto")
        
        if not all([cuenta_origen, cuenta_destino, monto]):
            return {"status": "ERROR", "error": "Datos incompletos"}
        
        monto = float(monto)
        cuenta_destino = int(cuenta_destino)  # Shibasito usa int
        
        with self.db_lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 1. Verificar saldo en Yapesito
                    cursor.execute("SELECT saldo FROM Cuentas WHERE id_cuenta = ?", (cuenta_origen,))
                    row = cursor.fetchone()
                    if not row or row[0] < monto:
                        return {"status": "ERROR", "error": "Saldo insuficiente"}
                    
                    # 2. Debitar de Yapesito
                    cursor.execute(
                        "UPDATE Cuentas SET saldo = saldo - ? WHERE id_cuenta = ?",
                        (monto, cuenta_origen)
                    )
                    cursor.execute(
                        "INSERT INTO Transacciones (id_cuenta, tipo, monto, referencia) VALUES (?, ?, ?, ?)",
                        (cuenta_origen, "DEBITO_INTERBANCARIO", monto, f"A Shibasito cuenta {cuenta_destino}")
                    )
                    
                    conn.commit()
                    print(f"[Yapesito] ✓ Débito exitoso: {cuenta_origen} -S/ {monto}")
                    
                # 3. Notificar a Shibasito (sin esperar respuesta)
                msg_shibasito = json.dumps({
                    "type": "CREDITO_INTERBANCARIO",
                    "cuenta_destino": cuenta_destino,
                    "monto": monto,
                    "banco_origen": "YAPESITO"
                })
                
                self.channel.basic_publish(
                    exchange='',
                    routing_key='shibasito_interbancaria_queue',
                    body=msg_shibasito.encode('utf-8')
                )
                
                print(f"[Yapesito] ✓ Notificación enviada a Shibasito cuenta {cuenta_destino}")
                return {"status": "OK", "message": "Transferencia interbancaria exitosa"}
                
            except Exception as e:
                print(f"[Yapesito] Error en transferencia interbancaria: {e}")
                import traceback
                traceback.print_exc()
                return {"status": "ERROR", "error": str(e)}

    def _handle_historial(self, req):
        """Consulta historial de transacciones"""
        cuenta = req.get("account")
        limit = req.get("limit", 20)

        if not cuenta:
            return {"status": "ERROR", "error": "Cuenta requerida"}

        with self.db_lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(
                        """SELECT id_transaccion, tipo, monto, fecha, referencia 
                           FROM Transacciones 
                           WHERE id_cuenta = ? 
                           ORDER BY fecha DESC 
                           LIMIT ?""",
                        (cuenta, limit)
                    )
                    rows = cursor.fetchall()

                    transacciones = [
                        {
                            "id": row["id_transaccion"],
                            "tipo": row["tipo"],
                            "monto": row["monto"],
                            "fecha": row["fecha"],
                            "referencia": row["referencia"],
                        }
                        for row in rows
                    ]

                    return {
                        "status": "OK",
                        "data": {"transacciones": transacciones},
                    }
            except Exception as e:
                print(f"[Yapesito] Error consultando historial: {e}")
                return {"status": "ERROR", "error": str(e)}

    def start(self):
        """Inicia el servidor"""
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=YAPESITO_QUEUE, on_message_callback=self.on_message
        )
        try:
            print("[Yapesito] ✓ Servidor iniciado. Esperando mensajes...", flush=True)
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.connection.close()
            print("\n[Yapesito] Servidor detenido.")


if __name__ == "__main__":
    print("=" * 50)
    print("    SERVIDOR YAPESITO - BANCO SIMPLE")
    print("=" * 50)

    # Verificar que existe la BD
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] No se encuentra la base de datos: {DB_PATH}")
        print("Ejecuta primero: sqlite3 {DB_PATH} < scripts_bd/bd_yapesito.sql")
        sys.exit(1)

    try:
        servidor = ServidorYapesito()
        servidor.start()
    except KeyboardInterrupt:
        print("\n[Yapesito] Interrumpido por usuario")
        sys.exit(0)
    except Exception as e:
        print(f"[Yapesito] ✗ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
