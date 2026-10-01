from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .models import APISection, Alert, AuditLog, ProcessStage
from .services import create_default_documents, create_default_stages, enqueue_alert_email, log_action, refresh_section_status


# Al crear una seccion se inicializa automaticamente el flujo BPM completo.
@receiver(post_save, sender=APISection)
def ensure_default_stages(sender, instance, created, **kwargs):
    if created:
        create_default_stages(instance)
        log_action(AuditLog.Action.SECTION_CREATED, section=instance)


# Al crear una etapa se agregan sus documentos base y se recalcula la seccion.
@receiver(post_save, sender=ProcessStage)
def ensure_default_stage_documents(sender, instance, created, **kwargs):
    if created:
        create_default_documents(instance)
    refresh_section_status(instance.section)


# Envía el correo después de confirmar la alerta y sus destinatarios en la base de datos.
@receiver(m2m_changed, sender=Alert.recipients.through)
def email_alert_recipients(sender, instance, action, pk_set, **kwargs):
    if action != "post_add" or not pk_set:
        return
    alert_id = instance.pk
    recipient_ids = tuple(pk_set)
    enqueue_alert_email(alert_id, recipient_ids)
