# -*- coding: utf-8 -*-
from __future__ import print_function

from Plugins.Plugin import PluginDescriptor


def main(session, **kwargs):
    from .ui import PiconUpdaterMain
    session.open(PiconUpdaterMain)


def Plugins(**kwargs):
    return PluginDescriptor(
        name="PiconUpdater",
        description="Picon catalog, updater and installer for Enigma2",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="icon.png",
        fnc=main,
    )
