-- Base de Datos de Yapesito
DROP TABLE IF EXISTS Transacciones;
DROP TABLE IF EXISTS Cuentas;

CREATE TABLE Cuentas (
    id_cuenta TEXT PRIMARY KEY,
    nombre_cliente TEXT NOT NULL,
    dni TEXT NOT NULL UNIQUE,
    saldo REAL NOT NULL CHECK (saldo >= 0),
    fecha_apertura TEXT DEFAULT (datetime('now'))
);

CREATE TABLE Transacciones (
    id_transaccion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cuenta TEXT NOT NULL,
    tipo TEXT NOT NULL,
    monto REAL NOT NULL,
    fecha TEXT DEFAULT (datetime('now')),
    referencia TEXT,
    FOREIGN KEY (id_cuenta) REFERENCES Cuentas(id_cuenta)
);

-- Datos iniciales
INSERT INTO Cuentas (id_cuenta, nombre_cliente, dni, saldo) VALUES
('YAP-5001', 'CARLOS ALBERTO RAMÍREZ SOTO', '87654321', 3500.00),
('YAP-5002', 'JOSÉ MIGUEL TORRES VEGA', '98765432', 2200.00),
('YAP-5003', 'LUCÍA PATRICIA MENDOZA DÍAZ', '23456789', 4100.00),
('YAP-5004', 'MIGUEL ÁNGEL CASTILLO ROJAS', '34567891', 1800.00),
('YAP-5005', 'ANDREA SOFÍA VARGAS LUNA', '45678923', 5300.00);

-- Transacciones de ejemplo
INSERT INTO Transacciones (id_cuenta, tipo, monto, referencia) VALUES
('YAP-5001', 'DEPOSITO', 1000.00, 'Depósito inicial'),
('YAP-5002', 'CREDITO', 500.00, 'Transferencia recibida'),
('YAP-5003', 'DEBITO', 200.00, 'Pago de servicio');
