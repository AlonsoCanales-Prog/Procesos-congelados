import psutil
import time
import threading
from collections import deque

UMBRAL_CONGELADO = 30  # Segundos en 0% CPU para marcar como congelado
MEMORIA_MINIMA_MB = 50  # Evitar procesos irrelevantes
INTERVALO_MONITOREO = 5  # Segundos entre revisiones

# Historial de CPU, RAM e I/O por proceso
historial_procesos = {}

# **Corrección: Forzar el cálculo de uso de CPU**
for proceso in psutil.process_iter():
    try:
        proceso.cpu_percent(interval=None)  # Primera llamada para inicializar medición
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

def monitorear_procesos():
    while True:
        for proceso in psutil.process_iter(['pid', 'name', 'memory_info', 'io_counters', 'status']):
            try:
                pid = proceso.info['pid']
                nombre = proceso.info['name']
                memoria = proceso.info['memory_info'].rss / (1024 * 1024)  # Convertir a MB
                estado = proceso.info['status']
                io_counters = proceso.info.get('io_counters', None)

                # **Corrección: Obtener CPU correctamente**
                cpu_uso = proceso.cpu_percent(interval=None)

                # Filtrar procesos con menos de 50MB de RAM
                if memoria < MEMORIA_MINIMA_MB:
                    continue  

                # Iniciar historial si es la primera vez
                if pid not in historial_procesos:
                    historial_procesos[pid] = {
                        'cpu': deque(maxlen=UMBRAL_CONGELADO // INTERVALO_MONITOREO),
                        'ram': deque(maxlen=UMBRAL_CONGELADO // INTERVALO_MONITOREO),
                        'io': deque(maxlen=UMBRAL_CONGELADO // INTERVALO_MONITOREO)
                    }

                historial = historial_procesos[pid]
                historial['cpu'].append(cpu_uso)
                historial['ram'].append(memoria)

                # Registrar actividad de I/O
                if io_counters:
                    io_total = io_counters.read_count + io_counters.write_count
                    historial['io'].append(io_total)
                else:
                    historial['io'].append(None)

                # Verificar si la RAM se mantiene constante en los últimos 30s
                sin_cambio_ram = len(historial['ram']) == historial['ram'].maxlen and historial['ram'][0] == historial['ram'][-1]
                sin_cambio_io = len(historial['io']) == historial['io'].maxlen and historial['io'][0] == historial['io'][-1]

                # Calcular promedio de uso de CPU
                promedio_cpu = sum(historial['cpu']) / len(historial['cpu']) if historial['cpu'] else 0

                # Verificar si el proceso está congelado
                if promedio_cpu == 0.0 and sin_cambio_ram and sin_cambio_io:
                    print(f"El proceso {nombre} (PID {pid}) podría estar congelado "
                          f"(CPU: {cpu_uso}%, RAM: {memoria:.2f}MB, Estado: {estado})")

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue  # Ignorar errores

        time.sleep(INTERVALO_MONITOREO)

# Crear y ejecutar el hilo de monitoreo
hilo_monitoreo = threading.Thread(target=monitorear_procesos, daemon=True)
hilo_monitoreo.start()

# Mantener el programa corriendo
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Monitoreo detenido.")
