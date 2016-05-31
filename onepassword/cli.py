import getpass
import os
import sys

import click
import pyperclip

from .keychain import Keychain

DEFAULT_KEYCHAIN_PATH = "~/Dropbox/1Password.agilekeychain"

try:
    EX_DATAERR = os.EX_DATAERR
except AttributeError:
    # os.EX_DATAERR is only available on Unix
    EX_DATAERR = 65


cli = click.Group(context_settings=dict(help_option_names=['-h', '--help']))

keychain_option = click.option('--path', envvar='ONEPASSWORD_KEYCHAIN',
                               default=DEFAULT_KEYCHAIN_PATH,
                               help="Path to your 1Password.agilekeychain file")

@cli.command('unlock')
@click.argument('item')
@keychain_option
@click.option('--fuzzy', is_flag=True,
              help="Perform fuzzy matching on the item")
@click.option('--no-prompt', is_flag=True,
              help="Don't prompt for a password, read from STDIN instead")
def unlock_password(item, path, fuzzy, no_prompt):
    try:
        keychain = Keychain(path)

        if no_prompt:
            password = sys.stdin.read().strip()
            keychain.unlock(password)
            if keychain.locked:
                click.echo("1pass: Incorrect master password", err=True)
                sys.exit(EX_DATAERR)
        else:
            while keychain.locked:
                keychain.unlock(getpass.getpass("Master password: "))

        found_item = keychain.item(item, 70 if fuzzy else 100)

        if found_item is not None:
            pyperclip.copy(found_item.password)
            click.echo("Password into clipboard!")
        else:
            click.echo("1pass: Could not find an item named '%s'" % (item), err=True)
            sys.exit(EX_DATAERR)
    except Exception as e:
        raise click.ClickException(str(e))


@cli.command('list')
@keychain_option
def list_items(path):
    try:
        keychain = Keychain(path)
        for item in keychain.list_items():
            click.echo(item)
    except Exception as e:
        raise click.ClickException(str(e))
