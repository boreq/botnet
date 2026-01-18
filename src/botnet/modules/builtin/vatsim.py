import threading
from .. import BaseResponder
from ..lib import parse_command, get_url


class Vatsim(BaseResponder):
    """Various VATSIM related features.

    Example module config:

        "botnet": {
            "vatsim": {
                "metar_api_url": "https://metar.vatsim.net/metar.php?id=%s",
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'vatsim'

    default_config = {
        'metar_api_url': 'https://metar.vatsim.net/metar.php?id=%s',
    }

    @parse_command([('icao', 1)], launch_invalid=False)
    def command_metar(self, msg, args):
        """Returns a METAR for the given aiport.

        Syntax: metar ICAO
        """
        def f():
            r = get_url(self.config_get('metar_api_url') % args.icao[0])
            r.raise_for_status()
            if not r.text:
                self.respond(msg, 'Server didn\'t return an error but the response is empty.')
            else:
                self.respond(msg, r.text)
        t = threading.Thread(target=f)
        t.start()


mod = Vatsim
