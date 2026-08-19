from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=False,
        INSTALLED_APPS=(),
        ROOT_URLCONF=__name__,
        SECRET_KEY="sirenity-test",
    )

import django

django.setup()
