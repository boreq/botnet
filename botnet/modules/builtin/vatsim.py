import threading
from .. import BaseResponder
from ..lib import parse_command, get_url


class Vatsim(BaseResponder):
    """Various VATSIM related features.

    Example module config:

        "botnet": {
            "vatsim": {
                "metar_api_url": "http://metar.vatsim.net/metar.php?id=%s",
                "airport_api_url": "http://api.vateud.net/airports/%s.json",
                "atc_api_url": "http://api.vateud.net/online/atc/%s.json"
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'vatsim'

    default_config = {
        'metar_api_url': 'http://metar.vatsim.net/metar.php?id=%s',
        'airport_api_url': 'http://api.vateud.net/airports/%s.json',
        'atc_api_url': 'http://api.vateud.net/online/atc/%s.json',
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
                self.respond(msg, str(e))
        t = threading.Thread(target=f)
        t.start()

    @parse_command([('icao', 1)], launch_invalid=False)
    def command_airport(self, msg, args):
        """Returns airport data.

        Syntax: airport ICAO
        """
        text_format = "{icao} ({name}, {country}) EL{elevation} TA{ta} | {runways}"
        runway_text_format = "{number} CRS{course} LEN{length} ILS{ils}"

        def f():
            try:
                r = get_url(self.config_get('airport_api_url') % args.icao[0])
                data = r.json()
                # runways text
                runways = [runway_text_format.format(
                    number=r['number'],
                    course=r['course'],
                    length=r['length'],
                    ils='{crs}/{freq}MHz'.format(crs=r['ils_fac'], freq=r['ils_freq']) if r['ils'] else 'NONE'
                ) for r in data['data']['runways']]
                # main text
                text = text_format.format(
                    icao=data['icao'],
                    country=data['country']['name'],
                    name=data['data']['name'],
                    elevation=data['data']['elevation'],
                    ta=data['data']['ta'],
                    runways=', '.join(runways)
                )
                self.respond(msg, text)
            except Exception as e:
                self.respond(msg, str(e))
        t = threading.Thread(target=f)
        t.start()

    @parse_command([('icao', 1)], launch_invalid=False)
    def command_atc(self, msg, args):
        """Returns ATC data for a given country. Accepts common prefix of the
        country's ICAO codes as a parameter.

        Syntax: atc ICAO
        """
        text_format = "{callsign} {frequency}MHz"

        def f():
            try:
                r = get_url(self.config_get('atc_api_url') % args.icao[0])
                data = r.json()
                if len(data) > 0:
                    text = [
                        text_format.format(
                            callsign=a['callsign'],
                            frequency=a['frequency']
                        ) for a in data
                    ]
                    self.respond(msg, ' | '.join(text))
                else:
                    self.respond(msg, "No ATC found")
            except Exception as e:
                self.respond(msg, str(e))
        t = threading.Thread(target=f)
        t.start()


mod = Vatsim
