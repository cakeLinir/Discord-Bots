import datetime

def format_datetime(dt):
    """Formatiert ein datetime-Objekt in ein lesbares Format."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_current_utc_time():
    """Gibt die aktuelle UTC-Zeit zurück."""
    return datetime.datetime.now(datetime.timezone.utc)
