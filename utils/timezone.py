from datetime import timezone, timedelta


IST = timezone(
    timedelta(hours=5, minutes=30)
)


def utc_to_ist(timestamp):

    if timestamp.tzinfo is None:

        timestamp = timestamp.replace(
            tzinfo=timezone.utc
        )

    return timestamp.astimezone(IST)