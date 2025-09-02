from datetime import datetime
from flask import session
from config import db
from modelo.models import ActividadReciente, Usuario

# Función para registrar una nueva actividad
def registrar_actividad(accion, elemento):
    if 'usuario_id' in session:
        nueva_actividad = ActividadReciente(
            usuario_id=session['usuario_id'],
            accion=accion,
            elemento=elemento,
            fecha=datetime.utcnow()
        )
        db.session.add(nueva_actividad)
        db.session.commit()

# Función para obtener las actividades recientes
def obtener_actividades_recientes(limite=5):
    actividades = ActividadReciente.query.order_by(ActividadReciente.fecha.desc()).limit(limite).all()
    resultado = []
    
    for actividad in actividades:
        usuario = Usuario.query.get(actividad.usuario_id)
        nik_name = usuario.nik_name if usuario else "Usuario desconocido"
        
        # Formatear la fecha
        fecha_actual = datetime.utcnow()
        fecha_actividad = actividad.fecha
        
        if fecha_actividad.date() == fecha_actual.date():
            fecha_formateada = f"Hoy, {fecha_actividad.strftime('%H:%M')} hs"
        elif (fecha_actual.date() - fecha_actividad.date()).days == 1:
            fecha_formateada = f"Ayer, {fecha_actividad.strftime('%H:%M')} hs"
        else:
            fecha_formateada = fecha_actividad.strftime('%d/%m/%Y, %H:%M hs')
        
        resultado.append({
            'usuario': nik_name,
            'accion': actividad.accion,
            'elemento': actividad.elemento,
            'fecha': fecha_formateada
        })
    
    return resultado