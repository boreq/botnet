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
            try:
                r = get_url(self.config_get('metar_api_url') % args.icao[0])
                self.respond(msg, r.text)
            except Exception as e:
                self.respond(msg, 'Error: ' + str(e))
        t = threading.Thread(target=f)
        t.start()


mod = Vatsim
