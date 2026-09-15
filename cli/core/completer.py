"""Auto-completion engine for CLI slash commands."""

from prompt_toolkit.completion import Completer, Completion
from cli.config import SLASH_COMMANDS


class SlashCommandCompleter(Completer):
    """Auto-completion triggered when input starts with '/'."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/"):
            for cmd in SLASH_COMMANDS:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))
