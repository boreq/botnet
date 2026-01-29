from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Generator

from ...message import Message, Nick


@dataclass()
class ReceivedMessage:
    received_at: datetime
    message: Message


class LogLoader:
    def iter(self, log_path: str) -> Generator[ReceivedMessage, None, None]:
        """Iterates over the log file and yields ReceivedMessage objects."""
        with open(log_path, 'r', encoding='utf-8') as log_file:
            for line in log_file:
                parts = line.split(' ', 3)
                if len(parts) < 4:
                    continue

                if not parts[3].startswith('IRC: Received: '):
                    continue

                date_str = parts[0]
                time_str = parts[1].split(',')[0]
                timestamp_str = f"{date_str} {time_str}"
                received_at = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                received_at = received_at.replace(tzinfo=timezone.utc)


                message_text = parts[3].removeprefix('IRC: Received: ')
                message_text = message_text.strip()

                message = Message.new_from_string(message_text)
                if message.command == 'PRIVMSG' and message.params[0].startswith('@#'):
                    continue

                if message.command == 'PRIVMSG' and len(message.params) < 2:
                    continue

                if message.command == 'PRIVMSG' and len(message.params[1]) == 0:
                    continue

                try:
                    if message.nickname is not None:
                        Nick(message.nickname)
                except:
                    continue

                if message.command != 'PING' and message.command != 'PONG':
                    print(message_text)

                yield ReceivedMessage(received_at=received_at, message=message)
