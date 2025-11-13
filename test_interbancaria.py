#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, 'src/python/common')

from rpc_client import RpcClient

def test_interbancaria():
    client = RpcClient()
    client.connect()
    
    print("=== TEST: Transferencia Interbancaria ===")
    print("Shibasito (1001) → Yapesito (YAP-5001)")
    
    response = client.call({
        "type": "TRANSFERIR_INTERBANCARIA",
        "banco_destino": "YAPESITO",
        "cuenta_origen": 1001,
        "cuenta_destino": "YAP-5001",
        "monto": 150.0
    })
    
    print(f"\nRespuesta: {response}")
    client.close()

if __name__ == "__main__":
    test_interbancaria()
