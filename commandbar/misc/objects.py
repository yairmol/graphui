import argparse
from typing import TYPE_CHECKING, Any, Dict, Set, Union, cast

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QApplication
    from commandbar.utils import usertypes
    from commandbar.commands import command

commands: Dict[str, 'command.Command'] = {}
args = cast(argparse.Namespace, None)
debug_flags: Set[str] = set()
qapp = cast('QApplication', None)