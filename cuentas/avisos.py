from django.utils import timezone


def entrada_pendiente(entrada_programada, marco_entrada, ahora):
    """Usa el turno laborable del usuario y su marcación, obtenidos del servidor."""
    if entrada_programada is None or marco_entrada:
        return ()
    if timezone.localdate(entrada_programada) != timezone.localdate(ahora):
        return ()
    return ("Todavía no registras tu entrada de hoy.",)
