#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente Terminal Yapesito
Interfaz de línea de comandos para operaciones bancarias
"""

import json
import os
import sys

# Agregar path de common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))

from rpc_client import RpcClient


class ClienteYapesito:
    def __init__(self):
        self.rpc_client = RpcClient()
        self.cuenta_actual = None
        self.nombre_usuario = None
        self.dni_actual = None

    def conectar(self):
        """Conectar al servidor RabbitMQ"""
        try:
            self.rpc_client.connect()
            print("✓ Conectado al servidor Yapesito")
            return True
        except Exception as e:
            print(f"✗ Error de conexión: {e}")
            return False

    def login(self):
        """Autenticar usuario"""
        print("\n" + "=" * 50)
        print("           LOGIN - BANCO YAPESITO")
        print("=" * 50)

        dni = input("DNI (8 dígitos): ").strip()
        cuenta = input("Cuenta (ej: YAP-5001): ").strip()

        if not dni or not cuenta:
            print("✗ Datos incompletos")
            return False

        try:
            response = self.rpc_client.call(
                {"type": "LOGIN", "dni": dni, "account": cuenta},
                routing_key="yapesito_queue"
            )

            if response.get("status") == "OK":
                self.cuenta_actual = response.get("account")
                self.nombre_usuario = response.get("nombre")
                self.dni_actual = dni
                print(f"\n✓ Bienvenido/a, {self.nombre_usuario}!")
                return True
            else:
                print(f"✗ Error: {response.get('error', 'Credenciales inválidas')}")
                return False
        except Exception as e:
            print(f"✗ Error de conexión: {e}")
            return False

    def consultar_saldo(self):
        """Consultar saldo actual"""
        try:
            response = self.rpc_client.call(
                {"type": "CONSULTAR_CUENTA", "account": self.cuenta_actual},
                routing_key="yapesito_queue"
            )

            if response.get("status") == "OK":
                saldo = response.get("balance", 0.0)
                print(f"\n💰 Saldo actual: S/ {saldo:,.2f}")
            else:
                print(f"✗ Error: {response.get('error')}")
        except Exception as e:
            print(f"✗ Error: {e}")

    def transferir_yapesito(self):
        """Transferir a otra cuenta Yapesito"""
        print("\n--- Transferencia Yapesito ---")
        cuenta_destino = input("Cuenta destino (YAP-XXXX): ").strip()
        monto = input("Monto: ").strip()

        if not cuenta_destino or not monto:
            print("✗ Datos incompletos")
            return

        try:
            monto = float(monto)
            if monto <= 0:
                print("✗ Monto debe ser positivo")
                return

            confirmacion = input(f"¿Transferir S/ {monto:.2f} a {cuenta_destino}? (s/n): ")
            if confirmacion.lower() != 's':
                print("Operación cancelada")
                return

            response = self.rpc_client.call(
                {
                    "type": "TRANSFERIR_CUENTA",
                    "cuenta_origen": self.cuenta_actual,
                    "cuenta_destino": cuenta_destino,
                    "monto": monto,
                },
                routing_key="yapesito_queue"
            )

            if response.get("status") == "OK":
                print(f"✓ Transferencia exitosa")
            else:
                print(f"✗ Error: {response.get('error')}")
        except ValueError:
            print("✗ Monto inválido")
        except Exception as e:
            print(f"✗ Error: {e}")

    def transferir_shibasito(self):
        """Transferir a cuenta Shibasito (interbancaria)"""
        print("\n--- Transferencia a Shibasito (Interbancaria) ---")
        cuenta_destino = input("Cuenta Shibasito (número, ej: 1001): ").strip()
        monto = input("Monto: ").strip()

        if not cuenta_destino or not monto:
            print("✗ Datos incompletos")
            return

        try:
            cuenta_destino = int(cuenta_destino)
            monto = float(monto)
            
            if monto <= 0:
                print("✗ Monto debe ser positivo")
                return

            confirmacion = input(f"¿Transferir S/ {monto:.2f} a Shibasito cuenta {cuenta_destino}? (s/n): ")
            if confirmacion.lower() != 's':
                print("Operación cancelada")
                return

            response = self.rpc_client.call(
                {
                    "type": "TRANSFERIR_INTERBANCARIA",
                    "cuenta_origen": self.cuenta_actual,
                    "cuenta_destino": cuenta_destino,
                    "monto": monto,
                },
                routing_key="yapesito_queue"
            )

            if response.get("status") == "OK":
                print(f"✓ Transferencia interbancaria exitosa")
            else:
                print(f"✗ Error: {response.get('error')}")

        except ValueError:
            print("✗ Datos inválidos")
        except Exception as e:
            print(f"✗ Error: {e}")

    def ver_historial(self):
        """Ver historial de transacciones"""
        try:
            response = self.rpc_client.call(
                {"type": "CONSULTAR_HISTORIAL", "account": self.cuenta_actual, "limit": 15},
                routing_key="yapesito_queue"
            )

            if response.get("status") == "OK":
                transacciones = response.get("data", {}).get("transacciones", [])
                
                if not transacciones:
                    print("\n📭 No hay transacciones registradas")
                    return

                print("\n" + "=" * 80)
                print(f"{'ID':<6} {'TIPO':<25} {'MONTO':>12} {'FECHA':<20}")
                print("=" * 80)

                for tx in transacciones:
                    tx_id = tx.get("id", "N/A")
                    tipo = tx.get("tipo", "DESCONOCIDO")
                    monto = tx.get("monto", 0.0)
                    fecha = tx.get("fecha", "N/A")
                    
                    # Formatear fecha
                    if " " in fecha:
                        fecha = fecha.split(".")[0]  # Quitar microsegundos

                    signo = "+" if "CREDITO" in tipo else "-"
                    print(f"{tx_id:<6} {tipo:<25} {signo}S/ {monto:>9.2f} {fecha}")

                print("=" * 80)
                print(f"Total: {len(transacciones)} transacciones")
            else:
                print(f"✗ Error: {response.get('error')}")
        except Exception as e:
            print(f"✗ Error: {e}")

    def menu_principal(self):
        """Menú interactivo"""
        while True:
            print("\n" + "=" * 50)
            print(f"  BANCO YAPESITO - {self.nombre_usuario}")
            print(f"  Cuenta: {self.cuenta_actual}")
            print("=" * 50)
            print("1. Consultar saldo")
            print("2. Transferir a Yapesito")
            print("3. Transferir a Shibasito (interbancaria)")
            print("4. Ver historial")
            print("5. Salir")
            print("=" * 50)

            opcion = input("Seleccione opción: ").strip()

            if opcion == "1":
                self.consultar_saldo()
            elif opcion == "2":
                self.transferir_yapesito()
            elif opcion == "3":
                self.transferir_shibasito()
            elif opcion == "4":
                self.ver_historial()
            elif opcion == "5":
                print("\n¡Hasta pronto!")
                break
            else:
                print("✗ Opción inválida")

    def cerrar(self):
        """Cerrar conexión"""
        if self.rpc_client:
            self.rpc_client.close()


def main():
    cliente = ClienteYapesito()

    if not cliente.conectar():
        print("No se pudo conectar al servidor. Asegúrate que RabbitMQ y el servidor Yapesito estén corriendo.")
        sys.exit(1)

    if cliente.login():
        cliente.menu_principal()

    cliente.cerrar()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrumpido por usuario")
        sys.exit(0)
