import logging

import click

@click.option("--mac", envvar="VOLCANO_MAC", required=True)
@click.option("--interface", default=None)
@click.option("--debug/--normal", default=False)
@click.pass_context
def run(ctx, mac: str, interface: str, debug: bool):
    print("Hello!")
