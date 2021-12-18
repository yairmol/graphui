import sys
import argparse

from PyQt5.QtWidgets import QWidget

from commandbar.utils import standarddir
from commandbar.config import configinit
from commandbar.keyinput import eventfilter
from commandbar.utils import objreg
from commandbar.misc import cmdhistory, objects
from commandbar.utils import log

from app import Application
from mainwindow import MainWindow
from commands.stretch import calculate_stretch, StretchCalculator


def init_log(args):
    """Initialize logging.

    Args:
        args: The argparse namespace.
    """
    from commandbar.utils import log
    log.init_log(args)
    log.init.debug("Log initialized.")

def logfilter_error(logfilter):
    """Validate logger names passed to --logfilter.

    Args:
        logfilter: A comma separated list of logger names.
    """
    from commandbar.utils import log
    try:
        log.LogFilter.parse(logfilter)
    except log.InvalidLogFilterError as e:
        raise argparse.ArgumentTypeError(e)
    return logfilter


def debug_flag_error(flag):
    """Validate flags passed to --debug-flag.

    Available flags:
        debug-exit: Turn on debugging of late exit.
        pdb-postmortem: Drop into pdb on exceptions.
        no-sql-history: Don't store history items.
        no-scroll-filtering: Process all scrolling updates.
        log-requests: Log all network requests.
        log-cookies: Log cookies in cookie filter.
        log-scroll-pos: Log all scrolling changes.
        log-sensitive-keys: Log keypresses in passthrough modes.
        stack: Enable Chromium stack logging.
        chromium: Enable Chromium logging.
        wait-renderer-process: Wait for debugger in renderer process.
        avoid-chromium-init: Enable `--version` without initializing Chromium.
        werror: Turn Python warnings into errors.
        test-notification-service: Use the testing libnotify service.
    """
    valid_flags = ['debug-exit', 'pdb-postmortem', 'no-sql-history',
                   'no-scroll-filtering', 'log-requests', 'log-cookies',
                   'log-scroll-pos', 'log-sensitive-keys', 'stack', 'chromium',
                   'wait-renderer-process', 'avoid-chromium-init', 'werror',
                   'test-notification-service']

    if flag in valid_flags:
        return flag
    else:
        raise argparse.ArgumentTypeError("Invalid debug flag - valid flags: {}"
                                         .format(', '.join(valid_flags)))


def get_argparser():
    parser = argparse.ArgumentParser(prog='graphvi',
                                     description="graphvi")
    parser.add_argument('-B', '--basedir', help="Base directory for all "
                        "storage.")
    parser.add_argument('-C', '--config-py', help="Path to config.py.",
                        metavar='CONFIG')
    parser.add_argument('-s', '--set', help="Set a temporary setting for "
                        "this session.", nargs=2, action='append',
                        dest='temp_settings', default=[],
                        metavar=('OPTION', 'VALUE'))
    parser.add_argument('-V', '--version', help="Show version and quit.",
                        action='store_true')
    parser.add_argument('--desktop-file-name',
                        default="org.qutebrowser.qutebrowser",
                        help="Set the base name of the desktop entry for this "
                        "application. Used to set the app_id under Wayland. See "
                        "https://doc.qt.io/qt-5/qguiapplication.html#desktopFileName-prop")
    parser.add_argument('--untrusted-args',
                        action='store_true',
                        help="Mark all following arguments as untrusted, which "
                        "enforces that they are URLs/search terms (and not flags or "
                        "commands)")

    parser.add_argument('--json-args', help=argparse.SUPPRESS)
    parser.add_argument('--temp-basedir-restarted',
                        help=argparse.SUPPRESS,
                        action='store_true')

    # WORKAROUND to be able to restart from older qutebrowser versions into this one.
    # Should be removed at some point.
    parser.add_argument('--enable-webengine-inspector',
                        help=argparse.SUPPRESS,
                        action='store_true')

    debug = parser.add_argument_group('debug arguments')
    debug.add_argument('-l', '--loglevel', dest='loglevel',
                       help="Override the configured console loglevel",
                       choices=['critical', 'error', 'warning', 'info',
                                'debug', 'vdebug'])
    debug.add_argument('--logfilter', type=logfilter_error,
                       help="Comma-separated list of things to be logged "
                       "to the debug log on stdout.")
    debug.add_argument('--loglines',
                       help="How many lines of the debug log to keep in RAM "
                       "(-1: unlimited).",
                       default=2000, type=int)
    debug.add_argument('-d', '--debug', help="Turn on debugging options.",
                       action='store_true')
    debug.add_argument('--json-logging', action='store_true', help="Output log"
                       " lines in JSON format (one object per line).")
    debug.add_argument('--nocolor', help="Turn off colored logging.",
                       action='store_false', dest='color')
    debug.add_argument('--force-color', help="Force colored logging",
                       action='store_true')
    debug.add_argument('--nowindow', action='store_true', help="Don't show "
                       "the main window.")
    debug.add_argument('-T', '--temp-basedir', action='store_true', help="Use "
                       "a temporary basedir.")
    debug.add_argument('--no-err-windows', action='store_true', help="Don't "
                       "show any error windows (used for tests/smoke.py).")
    debug.add_argument('--qt-arg', help="Pass an argument with a value to Qt. "
                       "For example, you can do "
                       "`--qt-arg geometry 650x555+200+300` to set the window "
                       "geometry.", nargs=2, metavar=('NAME', 'VALUE'),
                       action='append')
    debug.add_argument('--qt-flag', help="Pass an argument to Qt as flag.",
                       nargs=1, action='append')
    debug.add_argument('-D', '--debug-flag', type=debug_flag_error,
                       default=[], help="Pass name of debugging feature to be"
                       " turned on.", action='append', dest='debug_flags')
    parser.add_argument('command', nargs='*', help="Commands to execute on "
                        "startup.", metavar=':command')
    return parser


def early_init(args):
    init_log(args)


def on_focus_changed(_old, new):
    """Register currently focused main window in the object registry."""
    if new is None:
        return

    if not isinstance(new, QWidget):
        log.misc.debug("on_focus_changed called with non-QWidget {!r}".format(
            new))
        return

    window = new.window()
    if isinstance(window, MainWindow):
        objreg.register('last-focused-main-window', window, update=True)
        # A focused window must also be visible, and in this case we should
        # consider it as the most recently looked-at window
        objreg.register('last-visible-main-window', window, update=True)


def init(args):
    standarddir.init(args)
    # resources.preload()
    configinit.early_init(args)
    app = Application(args)
    objects.qapp = app
    cmdhistory.init()
    eventfilter.init()
    objects.qapp.focusChanged.connect(on_focus_changed)
        

def main():
    parser = get_argparser()
    args = parser.parse_args()
    init(args)
    window = MainWindow()
    window.show()
    objects.qapp.setActiveWindow(window)
    objects.qapp.exec_()


if __name__ == "__main__":
    main()



# def force_atals_graph_layout(G: nx.Graph, w: int, h: int):
#     positions = force_atlas2_layout(G, iterations=1000)
#     r1 = (-10, 10)
#     return {
#         u: (int(normalise(x, r1, (20, w - 20))), int(normalise(y, r1, (20, h - 20))))
#         for u, (x, y) in positions.items()
#     }