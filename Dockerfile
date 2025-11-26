# Usa una imagen base de Python oficial, por ejemplo la versión 3.10 slim
FROM python:3.12.3

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /home/servidor/Programas-automatizaciones/Conexion-Odoo-con-Google-Merchant

# Copia los archivos requirements.txt y los instala
# Se hace en dos pasos para aprovechar el cache de Docker si solo cambia el script
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de tu aplicación (incluyendo tu script Python)
COPY . .

# Comando para ejecutar tu script cuando el contenedor se inicie
# Reemplaza 'tu_script.py' con el nombre real de tu script
CMD ["python", "google_merchant_sync.py"]
