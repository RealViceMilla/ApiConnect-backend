from .services import generate_due_alerts, sync_role_groups


# Tarea reutilizable para generar alertas diarias por vencimientos.
def generate_daily_alerts():
    return generate_due_alerts()


# Tarea reutilizable para sincronizar grupos y permisos base de Django.
def sync_security_groups():
    return sync_role_groups()
