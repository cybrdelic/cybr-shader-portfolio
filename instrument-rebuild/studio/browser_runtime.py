"""Headless browser discovery without Linux display-server assumptions."""
from pathlib import Path
import os
import shutil
import sys


class HeadlessDisplay:
    def terminate(self):
        pass


def start_display():
    # Playwright's headless Chromium does not need Xvfb on any supported OS.
    return HeadlessDisplay()


def browser_path(playwright):
    explicit = os.environ.get('CYBR_BROWSER_PATH')
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise FileNotFoundError('CYBR_BROWSER_PATH is not a browser executable: ' + str(path))
        return str(path)
    bundled = Path(playwright.chromium.executable_path)
    if bundled.is_file():
        return str(bundled)
    candidates = [shutil.which(name) for name in ('chromium', 'chromium-browser', 'google-chrome', 'chrome', 'msedge')]
    if sys.platform == 'win32':
        for variable in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
            root = os.environ.get(variable)
            if root:
                candidates.extend(str(Path(root) / name) for name in (
                    'Google/Chrome/Application/chrome.exe', 'Microsoft/Edge/Application/msedge.exe'))
    elif sys.platform == 'darwin':
        candidates += ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                       '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge']
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise FileNotFoundError('Install Chromium with python -m playwright install chromium, or set CYBR_BROWSER_PATH.')


def launch_browser(playwright):
    args = []
    if os.environ.get('CYBR_SOFTWARE_GL') == '1':
        args += ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']
    return playwright.chromium.launch(executable_path=browser_path(playwright), headless=True, args=args)
