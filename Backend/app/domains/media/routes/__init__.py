from flask import Blueprint

media_bp = Blueprint("media", __name__)

from . import upload_intent as _upload_intent  # noqa: F401,E402
from . import complete as _complete  # noqa: F401,E402
from . import download_url as _download_url  # noqa: F401,E402
from . import list_archivos as _list_archivos  # noqa: F401,E402
from . import delete_archivo as _delete_archivo  # noqa: F401,E402
