# Sistema de Gestión de Préstamos Financieros

Aplicación de escritorio desarrollada en **Python** con interfaz gráfica **Tkinter** y persistencia relacional en **Microsoft SQL Server**.

## Características Principales
- **Registro de Clientes:** Alta y administración de datos personales.
- **Otorgamiento de Préstamos:** Cálculo automático de intereses, fecha de vencimiento ajustada a días de plazo y montos totales a devolver (precisión Decimal).
- **Tablero de Préstamos Activos:** Ordenamiento prioritario dinámico por proximidad de fecha de vencimiento (ASC).
- **Gestión y Liquidación:** Módulo de rectificación de plazos/fechas y cobro/cancelación en un clic.
- **Historial de Operaciones:** Pestaña de auditoría para préstamos liquidados.

## Tecnologías
- **Lenguaje:** Python 3.x
- **Interfaz Gráfica:** Tkinter (ttk)
- **Base de Datos:** Microsoft SQL Server
- **Conector BD:** pyodbc (ODBC Driver 17 for SQL Server)

## Instalación y Configuración

1. **Clonar el repositorio:**
   git clone https://github.com/TU_USUARIO/gestion-prestamos.git
   cd gestion-prestamos

2. **Instalar dependencias:**
   pip install -r requirements.txt

3. **Base de Datos:**
   - Ejecutar el script database/schema.sql en SQL Server Management Studio (SSMS) para crear la BD y las tablas.

4. **Ejecución:**
   python src/myapp.py

## Novedades de la Versión Final

- **Cálculo de mora en tiempo real:** Muestra los días de demora y el recargo acumulado dinámicamente mediante consultas en SQL Server.
- **Historial de Cancelados:** Separación de préstamos activos y liquidados, congelando los recargos al momento de cobrarlos.
- **Gestión y ajuste:** Posibilidad de corregir plazos, fechas y liquidar préstamos con confirmación en pantalla.
