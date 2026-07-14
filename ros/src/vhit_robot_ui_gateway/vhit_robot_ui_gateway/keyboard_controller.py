from __future__ import annotations

import os
import select
import sys
import termios
import tty
from collections.abc import Callable

from rclpy.node import Node


class KeyboardController:
    """Non-blocking keyboard input for temporary terminal-based jogging."""

    LEFT_ARROW = b"\x1b[D"
    RIGHT_ARROW = b"\x1b[C"

    def __init__(
        self,
        node: Node,
        on_left: Callable[[], None],
        on_right: Callable[[], None],
        poll_period: float = 0.05,
    ) -> None:
        self._node = node
        self._on_left = on_left
        self._on_right = on_right
        self._input_buffer = bytearray()

        if not sys.stdin.isatty():
            raise RuntimeError(
                "Keyboard control requires an interactive terminal"
            )

        self._stdin_fd = sys.stdin.fileno()
        self._original_terminal_settings = termios.tcgetattr(
            self._stdin_fd
        )

        # cbreak mode allows reading keys immediately without waiting for Enter.
        # Unlike full raw mode, Ctrl+C continues to work normally.
        tty.setcbreak(self._stdin_fd)

        self._timer = node.create_timer(
            poll_period,
            self._poll_keyboard,
        )

        node.get_logger().info(
            "Keyboard control enabled:\n"
            "  Left arrow  : negative jog\n"
            "  Right arrow : positive jog\n"
            "  Q           : quit"
        )

    def _poll_keyboard(self) -> None:
        readable, _, _ = select.select(
            [self._stdin_fd],
            [],
            [],
            0.0,
        )

        if readable:
            data = os.read(self._stdin_fd, 32)
            self._input_buffer.extend(data)

        self._process_input_buffer()

    def _process_input_buffer(self) -> None:
        while self._input_buffer:
            if self._input_buffer.startswith(self.LEFT_ARROW):
                del self._input_buffer[: len(self.LEFT_ARROW)]
                self._node.get_logger().info("Left arrow: negative jog")
                self._on_left()
                continue

            if self._input_buffer.startswith(self.RIGHT_ARROW):
                del self._input_buffer[: len(self.RIGHT_ARROW)]
                self._node.get_logger().info("Right arrow: positive jog")
                self._on_right()
                continue

            # An escape sequence may have arrived only partially.
            if self._input_buffer[0] == 0x1B:
                if len(self._input_buffer) < 3:
                    return

                # Unknown complete escape sequence.
                del self._input_buffer[0]
                continue

            key = bytes([self._input_buffer.pop(0)])

            if key in (b"q", b"Q"):
                self._node.get_logger().info(
                    "Keyboard quit requested"
                )

                # Generate the same behavior as Ctrl+C.
                os.kill(os.getpid(), 2)
                return

    def close(self) -> None:
        """Restore the terminal to its original configuration."""

        if hasattr(self, "_timer"):
            self._timer.cancel()

        if hasattr(self, "_original_terminal_settings"):
            termios.tcsetattr(
                self._stdin_fd,
                termios.TCSADRAIN,
                self._original_terminal_settings,
            )