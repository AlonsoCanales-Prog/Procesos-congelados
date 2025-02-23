import psutil
import time
import threading
from collections import deque

UMBRAL_CONGELADO = 30 #Segundos en 0% CPU para marcar como congelado
MEMORIA_MINIMA_MB = 400 #Evitar procesos irrelevantes (antes 10MB)
INTERVALO_MONITOREO = 5 #Segundos entre revisiones

#Historial de uso de CPU por proceso (ultimos 30-60s)
cpu_historial = {}

def monitorear_procesos():
    while True:
        for proceso in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
            try:
                pid = proceso.info['pid']
                nombre = proceso.info['name']
                cpu_uso = proceso.info['cpu_percent']
                memoria = proceso.info['memory_info'].rss / (1024 * 1024) #Convertir a MB
                estado = proceso.info['status']

                #Filtrar procesos con menos de 400MB de RAM
                if memoria < MEMORIA_MINIMA_MB:
                    continue  

                #Iniciar historial si es la primera vez
                if pid not in cpu_historial:
                    cpu_historial[pid] = deque(maxlen=12) #Ultimos 12 registros (60s si INTERVALO_MONITOREO = 5s)

                cpu_historial[pid].append(cpu_uso)

                #Calcular promedio de uso de CPU en los ultimos segundos
                promedio_cpu = sum(cpu_historial[pid]) / len(cpu_historial[pid])

                #Verificar si esta congelado (CPU 0% por 30s o mas)
                if promedio_cpu == 0.0:
                    print(f"El proceso {nombre} (PID {pid}) podría estar congelado "
                          f"(CPU: {cpu_uso}%, RAM: {memoria:.2f}MB, Estado: {estado})")

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue  #Ignorar errores

        time.sleep(INTERVALO_MONITOREO)

#Crear y ejecutar el hilo de monitoreo
hilo_monitoreo = threading.Thread(target=monitorear_procesos, daemon=True)
hilo_monitoreo.start()

#Mantener el programa corriendo para permitir la ejecucion del hilo
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Monitoreo detenido.")
