# Sistema Bancario Shibasito + Yapesito

Sistema bancario distribuido con arquitectura de microservicios usando RabbitMQ, implementando protocolo 2PC para transacciones atómicas y transferencias interbancarias.

## Arquitectura

- **Backend:** Java (ServidorCentral, NodoWorker) + Python (ReniecWorker, NodoWorker, ServidorYapesito)
- **Middleware:** RabbitMQ (patrón RPC)
- **Base de Datos:**
  - PostgreSQL: BD1_banco (Cuentas, Transacciones, Préstamos) - Shibasito
  - SQLite: BD2_reniec (Personas) - RENIEC
  - SQLite: BD_yapesito (Cuentas, Transacciones) - Yapesito
- **Cliente Desktop:** Python/Tkinter con generación de códigos QR de cobro
- **Cliente Terminal:** Cliente Yapesito para operaciones interbancarias
- **Distribución:** 2 particiones con 4 nodos workers

## Requisitos

- **Docker** (para RabbitMQ y PostgreSQL)
- **Java 11+** con JARs incluidos en `lib/`
- **Python 3.10+**
- **Git** (para clonar el repositorio)

## Instalación

### 1. Clonar repositorio

```bash
git clone <tu-repo>
cd PC3
```

### 2. Crear entorno virtual Python

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
```

### 3. Instalar dependencias Python

```bash
pip install -r requirements.txt
```

O manualmente:

```bash
pip install pika qrcode pillow psycopg2-binary
```

### 4. Iniciar servicios Docker

#### RabbitMQ:

```bash
docker run -d --name rabbitmq-server \
  -p 5672:5672 -p 15672:15672 \
  rabbitmq:3-management
```

#### PostgreSQL:

```bash
docker run -d --name postgres-db \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -p 5432:5432 postgres:13
```

**Verificar que estén corriendo:**

```bash
docker ps
```

### 5. Crear y poblar bases de datos

#### BD1 (Banco Shibasito - PostgreSQL):

```bash
# 1. Crear la base de datos vacía
docker exec -it postgres-db psql -U postgres -c "CREATE DATABASE bd1_banco;"

# 2. Cargar el schema y los datos
cat scripts_bd/bd1_banco.sql | docker exec -i postgres-db psql -U postgres -d bd1_banco
```

#### BD2 (RENIEC - SQLite):

```bash
# Crear la BD de RENIEC desde el dump
sqlite3 db_reniec/reniec.db < scripts_bd/bd2_reniec.sql
```

#### BD3 (Banco Yapesito - SQLite):

```bash
# Crear directorio y base de datos
mkdir -p src/python/yapesito
sqlite3 src/python/yapesito/db_yapesito.db < scripts_bd/bd_yapesito.sql

# Verificar creación
sqlite3 src/python/yapesito/db_yapesito.db "SELECT id_cuenta, nombre_cliente, saldo FROM Cuentas;"
```

**Salida esperada:**

```
YAP-5001|CARLOS ALBERTO RAMÍREZ SOTO|3500.0
YAP-5002|JOSÉ MIGUEL TORRES VEGA|2200.0
YAP-5003|LUCÍA PATRICIA MENDOZA DÍAZ|4100.0
YAP-5004|MIGUEL ÁNGEL CASTILLO ROJAS|1800.0
YAP-5005|ANDREA SOFÍA VARGAS LUNA|5300.0
```

### 6. Iniciar el sistema Shibasito

```bash
./scripts/iniciar_cluster.sh
```

**Salida esperada:**

```
✓ RabbitMQ está listo
✓ ServidorCentral iniciado
✓ ReniecWorker iniciado
✓ 4 NodosWorker iniciados
✓ ClienteProxy iniciado (puerto 9876)
```

### 7. Iniciar servidor Yapesito (terminal separada)

```bash
python3 src/python/yapesito/servidor_yapesito.py
```

**Salida esperada:**

```
==================================================
    SERVIDOR YAPESITO - BANCO SIMPLE
==================================================
[Yapesito] ✓ Conectado exitosamente a RabbitMQ
[Yapesito] ✓ Escuchando en cola 'yapesito_queue'
[Yapesito] ✓ Servidor iniciado. Esperando mensajes...
```

### 8. Ejecutar clientes

#### Cliente GUI Shibasito:

```bash
python src/python/cliente_desktop/cliente_gui.py
```

#### Cliente Terminal Yapesito:

```bash
python3 src/python/yapesito/cliente_yapesito.py
```

---

## Credenciales de Prueba

### Banco Shibasito:

| DNI        | Cuenta | Saldo Inicial | Nombre                      |
| ---------- | ------ | ------------- | --------------------------- |
| `45678912` | `1001` | S/ 2,400.00   | MARÍA ELENA GARCÍA FLORES   |
| `78901234` | `1002` | S/ 1,500.50   | JUAN CARLOS RAMÍREZ QUISPE  |
| `12345678` | `8008` | S/ 5,100.00   | LUIS ALBERTO TORRES MENDOZA |

### Banco Yapesito:

| DNI        | Cuenta     | Saldo Inicial | Nombre                      |
| ---------- | ---------- | ------------- | --------------------------- |
| `87654321` | `YAP-5001` | S/ 3,500.00   | CARLOS ALBERTO RAMÍREZ SOTO |
| `98765432` | `YAP-5002` | S/ 2,200.00   | JOSÉ MIGUEL TORRES VEGA     |
| `23456789` | `YAP-5003` | S/ 4,100.00   | LUCÍA PATRICIA MENDOZA DÍAZ |

---

## Transferencias Interbancarias

### 🔄 Transferencia: Shibasito → Yapesito

#### **Paso 1: Ver saldos iniciales**

**Shibasito (cuenta 1001):**

```bash
docker exec postgres-db psql -U postgres -d bd1_banco -c \
  "SELECT id_cuenta, nombre_cliente, saldo FROM Cuentas WHERE id_cuenta = 1001;"
```

**Salida esperada:**

```
 id_cuenta |    nombre_cliente         | saldo
-----------+---------------------------+--------
      1001 | MARÍA ELENA GARCÍA FLORES | 2400.00
```

**Yapesito (cuenta YAP-5001):**

```bash
sqlite3 src/python/yapesito/db_yapesito.db \
  "SELECT id_cuenta, nombre_cliente, saldo FROM Cuentas WHERE id_cuenta = 'YAP-5001';"
```

**Salida esperada:**

```
YAP-5001|CARLOS ALBERTO RAMÍREZ SOTO|3500.0
```

#### **Paso 2: Ejecutar transferencia**

Crear archivo `test_interbancaria_shibasito_yapesito.py`:

```python
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, 'src/python/common')

from rpc_client import RpcClient

def test_interbancaria():
    client = RpcClient()
    client.connect()

    print("=" * 60)
    print("  TEST: Transferencia Interbancaria")
    print("  Shibasito (1001) → Yapesito (YAP-5001)")
    print("  Monto: S/ 250.00")
    print("=" * 60)

    response = client.call({
        "type": "TRANSFERIR_INTERBANCARIA",
        "banco_destino": "YAPESITO",
        "cuenta_origen": 1001,
        "cuenta_destino": "YAP-5001",
        "monto": 250.0
    })

    print(f"\n✓ Respuesta del servidor:")
    print(f"  Status: {response.get('status')}")
    print(f"  Mensaje: {response.get('message', 'N/A')}")

    if response.get('status') == 'OK':
        print("\n✓ Transferencia interbancaria exitosa")
    else:
        print(f"\n✗ Error: {response.get('error')}")

    client.close()

if __name__ == "__main__":
    test_interbancaria()
```

**Ejecutar:**

```bash
python3 test_interbancaria_shibasito_yapesito.py
```

**Salida esperada:**

```
============================================================
  TEST: Transferencia Interbancaria
  Shibasito (1001) → Yapesito (YAP-5001)
  Monto: S/ 250.00
============================================================

✓ Respuesta del servidor:
  Status: OK
  Mensaje: Transferencia interbancaria exitosa

✓ Transferencia interbancaria exitosa
```

#### **Paso 3: Verificar saldos finales**

**Shibasito (debe haber disminuido en S/ 250):**

```bash
docker exec postgres-db psql -U postgres -d bd1_banco -c \
  "SELECT id_cuenta, nombre_cliente, saldo FROM Cuentas WHERE id_cuenta = 1001;"
```

**Salida esperada:**

```
 id_cuenta |    nombre_cliente         | saldo
-----------+---------------------------+--------
      1001 | MARÍA ELENA GARCÍA FLORES | 2150.00  ← Antes: 2400.00
```

**Yapesito (debe haber aumentado en S/ 250):**

```bash
sqlite3 src/python/yapesito/db_yapesito.db \
  "SELECT id_cuenta, nombre_cliente, saldo FROM Cuentas WHERE id_cuenta = 'YAP-5001';"
```

**Salida esperada:**

```
YAP-5001|CARLOS ALBERTO RAMÍREZ SOTO|3750.0  ← Antes: 3500.0
```

#### **Paso 4: Ver historial de transacciones**

**Transacción de débito en Shibasito:**

```bash
docker exec postgres-db psql -U postgres -d bd1_banco -c \
  "SELECT id_transaccion, tipo, monto, fecha FROM Transacciones WHERE id_cuenta = 1001 ORDER BY fecha DESC LIMIT 3;"
```

**Salida esperada:**

```
 id_transaccion |          tipo           |  monto  |            fecha
----------------+-------------------------+---------+----------------------------
            123 | DEBITO_INTERBANCARIO    |  250.00 | 2025-11-13 22:15:30.123456
            122 | CREDITO                 |  500.00 | 2025-11-13 21:30:00
            121 | DEBITO                  |  100.00 | 2025-11-13 20:00:00
```

**Transacción de crédito en Yapesito:**

```bash
sqlite3 src/python/yapesito/db_yapesito.db \
  "SELECT id_transaccion, tipo, monto, fecha, referencia FROM Transacciones WHERE id_cuenta = 'YAP-5001' ORDER BY fecha DESC LIMIT 3;"
```

**Salida esperada:**

```
15|CREDITO_INTERBANCARIO|250.0|2025-11-13 22:15:31|Desde SHIBASITO TX:abc-123-def
14|CREDITO|500.0|2025-11-13 21:00:00|Transferencia recibida
13|DEBITO|100.0|2025-11-13 20:30:00|Pago de servicio
```

---

### 🔄 Transferencia: Yapesito → Shibasito

#### **Paso 1: Ver saldos iniciales**

**Yapesito (cuenta YAP-5002):**

```bash
sqlite3 src/python/yapesito/db_yapesito.db \
  "SELECT id_cuenta, nombre_cliente, saldo FROM Cuentas WHERE id_cuenta = 'YAP-5002';"
```

**Salida esperada:**

```
YAP-5002|JOSÉ MIGUEL TORRES VEGA|2200.0
```

**Shibasito (cuenta 8008):**

```bash
docker exec postgres-db psql -U postgres -d bd1_banco -c \
  "SELECT id_cuenta, nombre_cliente, saldo FROM Cuentas WHERE id_cuenta = 8008;"
```

**Salida esperada:**

```
 id_cuenta |      nombre_cliente       |  saldo
-----------+---------------------------+---------
      8008 | LUIS ALBERTO TORRES MENDOZA| 5100.00
```

#### **Paso 2: Ejecutar transferencia desde cliente Yapesito**

```bash
python3 src/python/yapesito/cliente_yapesito.py
```

**En el menú:**

1. Login con:
   - DNI: `98765432`
   - Cuenta: `YAP-5002`

2. Seleccionar opción `3` (Transferir a Shibasito)

3. Ingresar:
   - Cuenta Shibasito: `8008`
   - Monto: `150`

4. Confirmar con `s`

**Salida esperada:**

```
--- Transferencia a Shibasito (Interbancaria) ---
Cuenta Shibasito (número, ej: 1001): 8008
Monto: 150
¿Transferir S/ 150.00 a Shibasito cuenta 8008? (s/n): s
✓ Transferencia interbancaria exitosa
```

#### **Paso 3: Verificar saldos finales**

**Yapesito (debe haber disminuido en S/ 150):**

```bash
sqlite3 src/python/yapesito/db_yapesito.db \
  "SELECT id_cuenta, nombre_cliente, saldo FROM Cuentas WHERE id_cuenta = 'YAP-5002';"
```

**Salida esperada:**

```
YAP-5002|JOSÉ MIGUEL TORRES VEGA|2050.0  ← Antes: 2200.0
```

**Shibasito (debe haber aumentado en S/ 150):**

```bash
docker exec postgres-db psql -U postgres -d bd1_banco -c \
  "SELECT id_cuenta, nombre_cliente, saldo FROM Cuentas WHERE id_cuenta = 8008;"
```

**Salida esperada:**

```
 id_cuenta |      nombre_cliente        |  saldo
-----------+----------------------------+---------
      8008 | LUIS ALBERTO TORRES MENDOZA | 5250.00  ← Antes: 5100.00
```

#### **Paso 4: Ver historial de transacciones**

**Transacción de débito en Yapesito:**

```bash
sqlite3 src/python/yapesito/db_yapesito.db \
  "SELECT id_transaccion, tipo, monto, fecha, referencia FROM Transacciones WHERE id_cuenta = 'YAP-5002' ORDER BY fecha DESC LIMIT 3;"
```

**Salida esperada:**

```
18|DEBITO_INTERBANCARIO|150.0|2025-11-13 22:30:45|A Shibasito cuenta 8008
17|CREDITO|300.0|2025-11-13 21:00:00|Transferencia recibida
16|DEBITO|50.0|2025-11-13 20:15:00|Pago de servicio
```

**Transacción de crédito en Shibasito:**

```bash
docker exec postgres-db psql -U postgres -d bd1_banco -c \
  "SELECT id_transaccion, tipo, monto, fecha FROM Transacciones WHERE id_cuenta = 8008 ORDER BY fecha DESC LIMIT 3;"
```

**Salida esperada:**

```
 id_transaccion |          tipo           |  monto  |            fecha
----------------+-------------------------+---------+----------------------------
            145 | CREDITO_INTERBANCARIO   |  150.00 | 2025-11-13 22:30:46.789012
            144 | CREDITO                 |  200.00 | 2025-11-13 21:45:00
            143 | DEBITO                  |   75.00 | 2025-11-13 20:30:00
```

---

## Resumen de Comandos Útiles

### Ver todos los saldos actuales:

**Shibasito:**

```bash
docker exec postgres-db psql -U postgres -d bd1_banco -c \
  "SELECT id_cuenta, nombre_cliente, saldo FROM Cuentas ORDER BY id_cuenta;"
```

**Yapesito:**

```bash
sqlite3 src/python/yapesito/db_yapesito.db \
  "SELECT id_cuenta, nombre_cliente, saldo FROM Cuentas ORDER BY id_cuenta;"
```

### Ver últimas 10 transacciones:

**Shibasito:**

```bash
docker exec postgres-db psql -U postgres -d bd1_banco -c \
  "SELECT t.id_transaccion, c.nombre_cliente, t.tipo, t.monto, t.fecha FROM Transacciones t JOIN Cuentas c ON t.id_cuenta = c.id_cuenta ORDER BY t.fecha DESC LIMIT 10;"
```

**Yapesito:**

```bash
sqlite3 src/python/yapesito/db_yapesito.db \
  "SELECT t.id_transaccion, c.nombre_cliente, t.tipo, t.monto, t.fecha FROM Transacciones t JOIN Cuentas c ON t.id_cuenta = c.id_cuenta ORDER BY t.fecha DESC LIMIT 10;"
```

### Ver solo transacciones interbancarias:

**Shibasito:**

```bash
docker exec postgres-db psql -U postgres -d bd1_banco -c \
  "SELECT * FROM Transacciones WHERE tipo LIKE '%INTERBANCARIO%' ORDER BY fecha DESC;"
```

**Yapesito:**

```bash
sqlite3 src/python/yapesito/db_yapesito.db \
  "SELECT * FROM Transacciones WHERE tipo LIKE '%INTERBANCARIO%' ORDER BY fecha DESC;"
```

---

## Funcionalidades

### Cliente Desktop Shibasito (GUI):

- **Login:** Validación con DNI + Cuenta (verificado contra RENIEC)
- **Consultar Saldo:** Visualización en tiempo real
- **Transferencias:** Entre cuentas Shibasito con protocolo 2PC
- **Transferencias Interbancarias:** A cuentas Yapesito (YAP-XXXX)
- **Préstamos:** Solicitud con validación de identidad
- **Historial:** Consulta de transacciones
- **Códigos QR:** Generación de QR de cobro para app móvil

### Cliente Terminal Yapesito:

- **Login:** Autenticación con DNI + Cuenta Yapesito
- **Consultar Saldo:** Saldo actual de la cuenta
- **Transferencias Yapesito:** Entre cuentas del mismo banco
- **Transferencias Interbancarias:** A cuentas Shibasito (numéricas)
- **Historial:** Ver últimas transacciones

### Backend:

- **Protocolo 2PC:** Transacciones atómicas distribuidas
- **Transferencias Interbancarias Bidireccionales:** Shibasito ↔ Yapesito
- **Particionamiento:** Distribución de cuentas en 2 particiones
- **Alta disponibilidad:** 2 réplicas por partición
- **Validación RENIEC:** Autenticación contra base de datos ciudadanos

---

## Detener Sistema

```bash
# Detener Shibasito
./scripts/detener_cluster.sh

# Detener Yapesito (Ctrl+C en terminal del servidor)

# Detener Docker (opcional)
docker stop rabbitmq-server postgres-db
```

---

## Arquitectura Técnica

### Componentes:

```
┌─────────────────┐     ┌─────────────────┐
│  Cliente GUI    │     │ Cliente Yapesito│
│  (Shibasito)    │     │   (Terminal)    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌────────────────────────────────────────┐
│            RabbitMQ (RPC)              │
│  client_requests_queue                 │
│  yapesito_queue                        │
│  shibasito_interbancaria_queue         │
└───────┬────────────────────────┬───────┘
        │                        │
        ▼                        ▼
┌───────────────┐        ┌──────────────┐
│ ServidorCentral│        │ServidorYapesito│
│  (Shibasito)  │◄──────►│  (Python)    │
└───────┬───────┘        └──────┬───────┘
        │                       │
        ▼                       ▼
┌───────────────┐        ┌─────────────┐
│  PostgreSQL   │        │   SQLite    │
│  (bd1_banco)  │        │ (yapesito)  │
└───────────────┘        └─────────────┘
```

---

## Estructura del Proyecto

```
PC3/
├── src/
│   ├── java/
│   │   ├── servidor_central/ServidorCentral.java
│   │   └── nodo_trabajador/NodoWorker.java
│   └── python/
│       ├── cliente_desktop/
│       │   ├── cliente_gui.py
│       │   └── cliente_proxy.py
│       ├── yapesito/
│       │   ├── servidor_yapesito.py      # Servidor Yapesito
│       │   └── cliente_yapesito.py       # Cliente terminal
│       ├── common/
│       │   ├── rpc_client.py
│       │   └── proxy_client.py
│       ├── nodo_reniec/reniec_worker.py
│       └── nodo_trabajador/nodo_worker.py
├── scripts_bd/
│   ├── bd1_banco.sql                     # Shibasito (PostgreSQL)
│   ├── bd2_reniec.sql                    # RENIEC (SQLite)
│   └── bd_yapesito.sql                   # Yapesito (SQLite)
└── README.md
```

---
