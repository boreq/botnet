import requests
from .. import BaseResponder
from ..lib import parse_command


class IPFS(BaseResponder):
    """Implements an interface to the IPFS daemon API. More or less experimental
    since the API has no documentation and behaves in a really weird way.

    Example module config:

        "botnet": {
            "ipfs": {
                "api_url": "http://127.0.0.1:5001",
            }
        }

    """

    config_namespace = 'botnet'
    config_name = 'ipfs'

    default_config = {
        'api_url': 'http://127.0.0.1:5001/api/v0/',
    }

    def api_get(self, url, *args, **kwargs):
        kwargs['arg'] = args
        url = '%s%s' % (self.config_get('api_url'), url)
        errors = []

        # Bail with simple error.
        try:
            r = requests.get(url, params=kwargs)
        except:
            raise Exception('Error. Is IPFS daemon running?')

        # Prepare more detailed error.
        try:
            r.raise_for_status()
        except:
            errors.append('IPFS API error.')

        j = None
        try:
            j = r.json()
        except:
            errors.append('API decided not to return JSON.')

        if j is not None and 'Message' in j:
            errors.append('Message: %s' % j['Message'])

        if errors:
            text = ' '.join(errors)
            raise Exception(text)

        return j

    @parse_command([('hash', 1)], launch_invalid=False)
    def admin_command_ipfs_pin(self, msg, args):
        """Pins an IPFS object.

        Syntax: ipfs_pin HASH
        """
        try:
            j = self.api_get('pin/add', *args.hash)
            if args.hash[0] in j.get('Pinned', []):
                self.respond(msg, 'Pinned %s!' % args.hash[0])
            else:
                self.respond(msg, 'Something went wrong.')
        except Exception as e:
            self.respond(msg, str(e))

    @parse_command([('hash', 1)], launch_invalid=False)
    def admin_command_ipfs_unpin(self, msg, args):
        """Unpins an IPFS object.

        Syntax: ipfs_unpin HASH
        """
        try:
            j = self.api_get('pin/rm', *args.hash)
            self.respond(msg, 'Unpinned %s!' % args.hash[0])
        except Exception as e:
            self.respond(msg, str(e))


mod = IPFS
