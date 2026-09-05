import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta
from decimal import Decimal
import pyodbc

# --- CONEXIÓN A LA BASE DE DATOS ---
def conectar_bd():
    try:
        conn = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=localhost;'
            'DATABASE=GestionPrestamos;'
            'Trusted_Connection=yes;'
        )
        return conn
    except Exception as e:
        messagebox.showerror("Error de Conexión", f"No se pudo conectar a SQL Server:\n{e}")
        return None

# --- LÓGICA DE CLIENTES ---
def registrar_cliente():
    nombre = entry_nombre.get().strip()
    apellido = entry_apellido.get().strip()
    telefono = entry_telefono.get().strip()
    
    if not nombre or not apellido:
        messagebox.showwarning("Datos incompletos", "Nombre y Apellido son obligatorios.")
        return
        
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Clientes (Nombre, Apellido, Telefono) VALUES (?, ?, ?)",
                (nombre, apellido, telefono)
            )
            conn.commit()
            messagebox.showinfo("Éxito", f"Cliente '{nombre} {apellido}' registrado correctamente.")
            entry_nombre.delete(0, tk.END)
            entry_apellido.delete(0, tk.END)
            entry_telefono.delete(0, tk.END)
            
            actualizar_combo_clientes()
            
        except Exception as e:
            messagebox.showerror("Error SQL", f"Falló al guardar el cliente:\n{e}")
        finally:
            conn.close()

def obtener_clientes():
    conn = conectar_bd()
    clientes = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT ClienteID, Nombre, Apellido FROM Clientes ORDER BY Apellido, Nombre")
            clientes = cursor.fetchall()
        finally:
            conn.close()
    return clientes

def actualizar_combo_clientes():
    clientes = obtener_clientes()
    combo_clientes['values'] = [f"{c.ClienteID} - {c.Apellido}, {c.Nombre}" for c in clientes]
    if clientes:
        combo_clientes.current(0)

# --- LÓGICA DE NEGOCIO DE PRÉSTAMOS ---
def registrar_prestamo():
    cliente_seleccionado = combo_clientes.get().strip()
    str_monto = entry_monto.get().strip()
    str_tasa = entry_tasa.get().strip()
    str_dias = entry_dias.get().strip()
    str_fecha_inicio = entry_fecha_inicio.get().strip()

    if not cliente_seleccionado or not str_monto or not str_tasa or not str_dias or not str_fecha_inicio:
        messagebox.showwarning("Campos Incompletos", "Por favor completa todos los campos del préstamo.")
        return

    try:
        if " - " in cliente_seleccionado:
            cliente_id = int(cliente_seleccionado.split(" - ")[0])
        else:
            messagebox.showerror("Error de Cliente", "Por favor selecciona un cliente válido de la lista.")
            return

        str_monto_limpio = str_monto.replace('.', '').replace(',', '.')
        monto = Decimal(str_monto_limpio)
        tasa = Decimal(str_tasa.replace(',', '.'))
        dias_plazo = int(str_dias)

        if monto <= 0 or tasa < 0 or dias_plazo <= 0:
            messagebox.showwarning("Atención", "Los valores numéricos deben ser mayores a cero.")
            return

        if "/" in str_fecha_inicio:
            fecha_inicio_dt = datetime.strptime(str_fecha_inicio, "%d/%m/%Y")
        else:
            fecha_inicio_dt = datetime.strptime(str_fecha_inicio, "%Y-%m-%d")

        interes_monto = monto * (tasa / Decimal(100))
        monto_total_devolver = monto + interes_monto
        fecha_vencimiento_dt = fecha_inicio_dt + timedelta(days=dias_plazo)

        fecha_inicio_str = fecha_inicio_dt.strftime('%Y-%m-%d')
        fecha_vencimiento_str = fecha_vencimiento_dt.strftime('%Y-%m-%d')

    except ValueError as ve:
        messagebox.showerror(
            "Error de Formato", 
            f"Verificá los datos ingresados.\n"
            f"Asegurate que la fecha tenga formato YYYY-MM-DD o DD/MM/YYYY.\n"
            f"Detalle: {ve}"
        )
        return
    except Exception as e:
        messagebox.showerror("Error Inesperado", f"Ocurrió un detalle al procesar los datos:\n{e}")
        return

    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO Prestamos 
                (ClienteID, MontoPrestado, TasaInteres, MontoTotalDevolver, FechaInicio, FechaVencimiento, Estado)
                VALUES (?, ?, ?, ?, ?, ?, 'Activo')
            """
            cursor.execute(query, (cliente_id, monto, tasa, monto_total_devolver, fecha_inicio_str, fecha_vencimiento_str))
            conn.commit()

            resumen = (
                f"Préstamo registrado con éxito:\n\n"
                f"• Monto Prestado: ${monto:,.2f}\n"
                f"• Tasa Interés: {tasa}%\n"
                f"• Total Base: ${monto_total_devolver:,.2f}\n"
                f"• Fecha Inicio: {fecha_inicio_str}\n"
                f"• Fecha Vencimiento: {fecha_vencimiento_str}"
            )
            messagebox.showinfo("Préstamo Generado", resumen)
            
            entry_monto.delete(0, tk.END)
            entry_tasa.delete(0, tk.END)
            entry_dias.delete(0, tk.END)
            entry_fecha_inicio.delete(0, tk.END)
            entry_fecha_inicio.insert(0, datetime.now().strftime('%Y-%m-%d'))

            actualizar_tabla_prestamos()

        except Exception as e:
            messagebox.showerror("Error SQL", f"Falló al registrar el préstamo en SQL Server:\n{e}")
        finally:
            conn.close()

# --- LÓGICA DE CONSULTA Y EDICIÓN DE PRÉSTAMOS ACTIVOS (CON MORA TIEMPO REAL) ---
def cargar_prestamos_por_estado(estado, orden="ASC"):
    conn = conectar_bd()
    prestamos = []
    if conn:
        try:
            cursor = conn.cursor()
            # Si el estado es 'Cancelado', la mora y recargos se fuerzan a 0
            query = f"""
                SELECT 
                    p.PrestamoID,
                    c.Nombre + ' ' + c.Apellido AS Cliente,
                    p.MontoPrestado,
                    p.MontoTotalDevolver,
                    CONVERT(VARCHAR(10), p.FechaInicio, 120) AS FechaInicio,
                    CONVERT(VARCHAR(10), p.FechaVencimiento, 120) AS FechaVencimiento,
                    DATEDIFF(day, CAST(p.FechaInicio AS DATE), CAST(p.FechaVencimiento AS DATE)) AS DiasPlazo,
                    CASE 
                        WHEN p.Estado = 'Cancelado' THEN 0
                        WHEN DATEDIFF(day, CAST(p.FechaVencimiento AS DATE), CAST(GETDATE() AS DATE)) > 0 
                        THEN DATEDIFF(day, CAST(p.FechaVencimiento AS DATE), CAST(GETDATE() AS DATE)) - 1
                        ELSE 0 
                    END AS DiasMora,
                    CASE 
                        WHEN p.Estado = 'Cancelado' THEN 0.0
                        WHEN DATEDIFF(day, CAST(p.FechaVencimiento AS DATE), CAST(GETDATE() AS DATE)) > 0 
                        THEN (DATEDIFF(day, CAST(p.FechaVencimiento AS DATE), CAST(GETDATE() AS DATE)) - 1) * 5000.0
                        ELSE 0.0 
                    END AS RecargoMora,
                    (p.MontoTotalDevolver + CASE 
                        WHEN p.Estado = 'Cancelado' THEN 0.0
                        WHEN DATEDIFF(day, CAST(p.FechaVencimiento AS DATE), CAST(GETDATE() AS DATE)) > 0 
                        THEN (DATEDIFF(day, CAST(p.FechaVencimiento AS DATE), CAST(GETDATE() AS DATE)) - 1) * 5000.0
                        ELSE 0.0 
                    END) AS TotalACobrar
                FROM Prestamos p
                INNER JOIN Clientes c ON p.ClienteID = c.ClienteID
                WHERE p.Estado = ?
                ORDER BY p.FechaVencimiento {orden}, p.PrestamoID {orden}
            """
            cursor.execute(query, (estado,))
            prestamos = cursor.fetchall()
        finally:
            conn.close()
    return prestamos

def actualizar_tabla_prestamos():
    # Limpiar y actualizar la tabla de Préstamos Activos
    for item in tree_prestamos.get_children():
        tree_prestamos.delete(item)
        
    prestamos_activos = cargar_prestamos_por_estado('Activo', orden="ASC")
    for row in prestamos_activos:
        tag = 'en_mora' if row.DiasMora > 0 else 'normal'
        tree_prestamos.insert('', tk.END, values=(
            row.PrestamoID,
            row.Cliente,
            f"${row.MontoPrestado:,.2f}",
            f"${row.MontoTotalDevolver:,.2f}",
            row.FechaInicio,
            row.FechaVencimiento,
            row.DiasPlazo,
            row.DiasMora if row.DiasMora > 0 else "-",
            f"${row.RecargoMora:,.2f}" if row.RecargoMora > 0 else "$0.00",
            f"${row.TotalACobrar:,.2f}"
        ), tags=(tag,))

    # Configuración de color para mora
    tree_prestamos.tag_configure('en_mora', foreground='red')
    tree_prestamos.tag_configure('normal', foreground='black')

    # Limpiar y actualizar la tabla de Préstamos Cancelados (Historial)
    for item in tree_cancelados.get_children():
        tree_cancelados.delete(item)

    prestamos_cancelados = cargar_prestamos_por_estado('Cancelado', orden="DESC")
    for row in prestamos_cancelados:
        tree_cancelados.insert('', tk.END, values=(
            row.PrestamoID,
            row.Cliente,
            f"${row.MontoPrestado:,.2f}",
            f"${row.MontoTotalDevolver:,.2f}",
            row.FechaInicio,
            row.FechaVencimiento,
            row.DiasPlazo,
            row.DiasMora if row.DiasMora > 0 else "-",
            f"${row.RecargoMora:,.2f}" if row.RecargoMora > 0 else "$0.00",
            f"${row.TotalACobrar:,.2f}"
        ))

def seleccionar_prestamo(event):
    selected = tree_prestamos.selection()
    if selected:
        item = tree_prestamos.item(selected[0])
        val = item['values']
        
        entry_edit_id.config(state='normal')
        entry_edit_id.delete(0, tk.END)
        entry_edit_id.insert(0, str(val[0]))
        entry_edit_id.config(state='readonly')
        
        entry_edit_fecha.delete(0, tk.END)
        entry_edit_fecha.insert(0, str(val[4]))
        
        entry_edit_dias.delete(0, tk.END)
        entry_edit_dias.insert(0, str(val[6]))

def guardar_edicion_prestamo():
    prestamo_id = entry_edit_id.get().strip()
    str_nueva_fecha = entry_edit_fecha.get().strip()
    str_nuevos_dias = entry_edit_dias.get().strip()

    if not prestamo_id or not str_nueva_fecha or not str_nuevos_dias:
        messagebox.showwarning("Atención", "Seleccioná un préstamo de la lista y completá los campos.")
        return

    try:
        dias_plazo = int(str_nuevos_dias)
        if dias_plazo <= 0:
            messagebox.showwarning("Atención", "El plazo debe ser mayor a 0.")
            return

        if "/" in str_nueva_fecha:
            fecha_inicio_dt = datetime.strptime(str_nueva_fecha, "%d/%m/%Y")
        else:
            fecha_inicio_dt = datetime.strptime(str_nueva_fecha, "%Y-%m-%d")

        fecha_vencimiento_dt = fecha_inicio_dt + timedelta(days=dias_plazo)

        nueva_inicio_str = fecha_inicio_dt.strftime('%Y-%m-%d')
        nueva_venc_str = fecha_vencimiento_dt.strftime('%Y-%m-%d')

    except ValueError as ve:
        messagebox.showerror("Error de Formato", f"Verificá los valores ingresados (Fecha YYYY-MM-DD / Días numéricos).\n{ve}")
        return

    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                UPDATE Prestamos
                SET FechaInicio = ?, FechaVencimiento = ?
                WHERE PrestamoID = ?
            """
            cursor.execute(query, (nueva_inicio_str, nueva_venc_str, int(prestamo_id)))
            conn.commit()

            messagebox.showinfo("Actualizado", f"Préstamo #{prestamo_id} corregido con éxito.\nNueva Fecha Vencimiento: {nueva_venc_str}")
            
            limpiar_panel_edicion()
            actualizar_tabla_prestamos()

        except Exception as e:
            messagebox.showerror("Error SQL", f"Falló al actualizar el préstamo:\n{e}")
        finally:
            conn.close()

def liquidar_prestamo():
    prestamo_id = entry_edit_id.get().strip()
    
    if not prestamo_id:
        messagebox.showwarning("Atención", "Seleccioná primero un préstamo de la lista para liquidar.")
        return

    # Obtener el valor actual de 'Total a Cobrar' directamente del ítem seleccionado
    selected = tree_prestamos.selection()
    monto_cobrado = "$0.00"
    if selected:
        monto_cobrado = tree_prestamos.item(selected[0])['values'][9]

    confirmar = messagebox.askyesno(
        "Confirmar Liquidación", 
        f"¿Confirmás que el cliente abonó {monto_cobrado} y querés liquidar el Préstamo #{prestamo_id}?\n\nPasará a la solapa de 'Préstamos Cancelados'."
    )
    
    if confirmar:
        conn = conectar_bd()
        if conn:
            try:
                cursor = conn.cursor()
                query = "UPDATE Prestamos SET Estado = 'Cancelado' WHERE PrestamoID = ?"
                cursor.execute(query, (int(prestamo_id),))
                conn.commit()

                messagebox.showinfo("Préstamo Liquidado", f"El Préstamo #{prestamo_id} fue marcado como Cancelado/Pagado y movido al Historial.")
                
                limpiar_panel_edicion()
                actualizar_tabla_prestamos()

            except Exception as e:
                messagebox.showerror("Error SQL", f"Falló al liquidar el préstamo:\n{e}")
            finally:
                conn.close()

def limpiar_panel_edicion():
    entry_edit_id.config(state='normal')
    entry_edit_id.delete(0, tk.END)
    entry_edit_id.config(state='readonly')
    entry_edit_fecha.delete(0, tk.END)
    entry_edit_dias.delete(0, tk.END)


# --- INTERFAZ GRÁFICA (TKINTER) ---
root = tk.Tk()
root.title("Sistema de Gestión de Préstamos")
root.geometry("1020x560")

# Control de Pestañas
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

# ----------------- PESTAÑA 1: CLIENTES -----------------
tab_clientes = ttk.Frame(notebook)
notebook.add(tab_clientes, text="  Clientes  ")

frame_c = ttk.LabelFrame(tab_clientes, text=" Datos del Cliente ", padding=15)
frame_c.pack(padx=15, pady=15, fill="both", expand=True)

ttk.Label(frame_c, text="Nombre:").grid(row=0, column=0, sticky="w", pady=5)
entry_nombre = ttk.Entry(frame_c, width=30)
entry_nombre.grid(row=0, column=1, pady=5)

ttk.Label(frame_c, text="Apellido:").grid(row=1, column=0, sticky="w", pady=5)
entry_apellido = ttk.Entry(frame_c, width=30)
entry_apellido.grid(row=1, column=1, pady=5)

ttk.Label(frame_c, text="Teléfono:").grid(row=2, column=0, sticky="w", pady=5)
entry_telefono = ttk.Entry(frame_c, width=30)
entry_telefono.grid(row=2, column=1, pady=5)

btn_guardar_cliente = ttk.Button(frame_c, text="Guardar Cliente", command=registrar_cliente)
btn_guardar_cliente.grid(row=3, column=0, columnspan=2, pady=15)

# ----------------- PESTAÑA 2: NUEVO PRÉSTAMO -----------------
tab_prestamos = ttk.Frame(notebook)
notebook.add(tab_prestamos, text="  Nuevo Préstamo  ")

frame_p = ttk.LabelFrame(tab_prestamos, text=" Registrar Préstamo ", padding=15)
frame_p.pack(padx=15, pady=15, fill="both", expand=True)

ttk.Label(frame_p, text="Seleccionar Cliente:").grid(row=0, column=0, sticky="w", pady=5)
combo_clientes = ttk.Combobox(frame_p, width=35, state="readonly")
combo_clientes.grid(row=0, column=1, pady=5)

ttk.Label(frame_p, text="Fecha Inicio (AAAA-MM-DD):").grid(row=1, column=0, sticky="w", pady=5)
entry_fecha_inicio = ttk.Entry(frame_p, width=20)
entry_fecha_inicio.grid(row=1, column=1, sticky="w", pady=5)
entry_fecha_inicio.insert(0, datetime.now().strftime('%Y-%m-%d'))

ttk.Label(frame_p, text="Monto a Prestar ($):").grid(row=2, column=0, sticky="w", pady=5)
entry_monto = ttk.Entry(frame_p, width=20)
entry_monto.grid(row=2, column=1, sticky="w", pady=5)

ttk.Label(frame_p, text="Tasa de Interés (%):").grid(row=3, column=0, sticky="w", pady=5)
entry_tasa = ttk.Entry(frame_p, width=20)
entry_tasa.grid(row=3, column=1, sticky="w", pady=5)

ttk.Label(frame_p, text="Plazo (en días):").grid(row=4, column=0, sticky="w", pady=5)
entry_dias = ttk.Entry(frame_p, width=20)
entry_dias.grid(row=4, column=1, sticky="w", pady=5)

btn_guardar_prestamo = ttk.Button(frame_p, text="Otorgar Préstamo", command=registrar_prestamo)
btn_guardar_prestamo.grid(row=5, column=0, columnspan=2, pady=15)

# ----------------- PESTAÑA 3: PRÉSTAMOS ACTIVOS Y LIQUIDACIÓN -----------------
tab_activos = ttk.Frame(notebook)
notebook.add(tab_activos, text="  Préstamos Activos  ")

frame_tabla = ttk.LabelFrame(tab_activos, text=" Listado de Préstamos Activos (Con Mora Calculada al Día) ", padding=10)
frame_tabla.pack(padx=10, pady=5, fill="both", expand=True)

columns = ('id', 'cliente', 'monto', 'total_base', 'f_inicio', 'f_venc', 'dias', 'dias_mora', 'recargo_mora', 'total_cobrar')
tree_prestamos = ttk.Treeview(frame_tabla, columns=columns, show='headings', height=8)

tree_prestamos.heading('id', text='ID')
tree_prestamos.heading('cliente', text='Cliente')
tree_prestamos.heading('monto', text='Monto Prestado')
tree_prestamos.heading('total_base', text='Total Base')
tree_prestamos.heading('f_inicio', text='F. Inicio')
tree_prestamos.heading('f_venc', text='F. Vencimiento')
tree_prestamos.heading('dias', text='Días')
tree_prestamos.heading('dias_mora', text='Días Mora')
tree_prestamos.heading('recargo_mora', text='Mora ($)')
tree_prestamos.heading('total_cobrar', text='Total a Cobrar')

tree_prestamos.column('id', width=35, anchor='center')
tree_prestamos.column('cliente', width=140)
tree_prestamos.column('monto', width=95, anchor='e')
tree_prestamos.column('total_base', width=95, anchor='e')
tree_prestamos.column('f_inicio', width=80, anchor='center')
tree_prestamos.column('f_venc', width=90, anchor='center')
tree_prestamos.column('dias', width=45, anchor='center')
tree_prestamos.column('dias_mora', width=65, anchor='center')
tree_prestamos.column('recargo_mora', width=85, anchor='e')
tree_prestamos.column('total_cobrar', width=105, anchor='e')

tree_prestamos.pack(fill="both", expand=True)
tree_prestamos.bind('<<TreeviewSelect>>', seleccionar_prestamo)

# Panel Inferior para Acciones
frame_edit = ttk.LabelFrame(tab_activos, text=" Gestión de Préstamo Seleccionado ", padding=10)
frame_edit.pack(padx=10, pady=5, fill="x")

ttk.Label(frame_edit, text="ID:").grid(row=0, column=0, padx=2, pady=5)
entry_edit_id = ttk.Entry(frame_edit, width=6, state='readonly')
entry_edit_id.grid(row=0, column=1, padx=2, pady=5)

ttk.Label(frame_edit, text="F. Inicio:").grid(row=0, column=2, padx=2, pady=5)
entry_edit_fecha = ttk.Entry(frame_edit, width=11)
entry_edit_fecha.grid(row=0, column=3, padx=2, pady=5)

ttk.Label(frame_edit, text="Días:").grid(row=0, column=4, padx=2, pady=5)
entry_edit_dias = ttk.Entry(frame_edit, width=6)
entry_edit_dias.grid(row=0, column=5, padx=2, pady=5)

btn_guardar_edit = ttk.Button(frame_edit, text="Guardar Cambios", command=guardar_edicion_prestamo)
btn_guardar_edit.grid(row=0, column=6, padx=8, pady=5)

btn_liquidar = ttk.Button(frame_edit, text="✔ Liquidar / Cobrado", command=liquidar_prestamo)
btn_liquidar.grid(row=0, column=7, padx=8, pady=5)

# ----------------- PESTAÑA 4: PRÉSTAMOS CANCELADOS (HISTORIAL) -----------------
tab_cancelados = ttk.Frame(notebook)
notebook.add(tab_cancelados, text="  Préstamos Cancelados  ")

frame_tabla_canc = ttk.LabelFrame(tab_cancelados, text=" Historial de Préstamos Liquidados ", padding=10)
frame_tabla_canc.pack(padx=10, pady=10, fill="both", expand=True)

tree_cancelados = ttk.Treeview(frame_tabla_canc, columns=columns, show='headings', height=12)

tree_cancelados.heading('id', text='ID')
tree_cancelados.heading('cliente', text='Cliente')
tree_cancelados.heading('monto', text='Monto Prestado')
tree_cancelados.heading('total_base', text='Total Base')
tree_cancelados.heading('f_inicio', text='F. Inicio')
tree_cancelados.heading('f_venc', text='F. Vencimiento')
tree_cancelados.heading('dias', text='Días')
tree_cancelados.heading('dias_mora', text='Días Mora')
tree_cancelados.heading('recargo_mora', text='Mora ($)')
tree_cancelados.heading('total_cobrar', text='Total a Cobrar')

tree_cancelados.column('id', width=35, anchor='center')
tree_cancelados.column('cliente', width=140)
tree_cancelados.column('monto', width=95, anchor='e')
tree_cancelados.column('total_base', width=95, anchor='e')
tree_cancelados.column('f_inicio', width=80, anchor='center')
tree_cancelados.column('f_venc', width=90, anchor='center')
tree_cancelados.column('dias', width=45, anchor='center')
tree_cancelados.column('dias_mora', width=65, anchor='center')
tree_cancelados.column('recargo_mora', width=85, anchor='e')
tree_cancelados.column('total_cobrar', width=105, anchor='e')

tree_cancelados.pack(fill="both", expand=True)

# Cargar datos iniciales
actualizar_combo_clientes()
actualizar_tabla_prestamos()

root.mainloop()