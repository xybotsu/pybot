import codecs
from jinja2 import (
    Environment, PackageLoader, FileSystemLoader, select_autoescape
)
import os
import subprocess
import tempfile
from pathlib import Path

MODULE_DIR = Path(__file__).parent.resolve()

WK_PATH = os.getenv(
    'WKHTMLTOIMAGE_PATH',
    str(MODULE_DIR / 'bin' / 'wkhtmltoimage-amd64')
)

DFT_CACHE_DIR = Path(tempfile.gettempdir()) / 'wk_cache'

env = Environment(
    loader=FileSystemLoader(str(MODULE_DIR / 'templates')),
    autoescape=select_autoescape(['html'])
)


def getCryptoLeaderboardPng(rows):
    template = env.get_template('cryptoLeaderboard.html')
    html = template.render(rows=rows)
    return generate_png(html)


def getCryptoTopPng(rows):
    template = env.get_template('cryptoTop.html')
    html = template.render(rows=rows)
    return generate_png(html)


def execute_wk(input):
    """
    Generate path for the wkhtmltoimage binary and execute command.

    :param args: args to pass straight to subprocess.Popen
    :return: stdout, stderr
    """
    return subprocess.run(
        "{path} --width 0 --format png --quality 35 - -".format(path=WK_PATH),
        input=input,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )


def generate_png(html: str):
    print(html.encode())
    p = execute_wk(html.encode())
    png_content = p.stdout
    if p.returncode != 0:
        raise RuntimeError('error running wkhtmltoimage, command')
    return png_content
