from datetime import datetime


def datetime_to_str(dt: datetime):
    return dt.strftime("%Y/%m/%d %H:%M:%S")
