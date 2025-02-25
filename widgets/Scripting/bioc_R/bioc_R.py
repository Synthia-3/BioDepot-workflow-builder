import os
import glob
import sys
import functools
import jsonpickle
from collections import OrderedDict
from Orange.widgets import widget, gui, settings
import Orange.data
from Orange.data.io import FileFormat
from DockerClient import DockerClient
from BwBase import OWBwBWidget, ConnectionDict, BwbGuiElements, getIconName, getJsonName
from PyQt5 import QtWidgets, QtGui


class OWbioc_R(OWBwBWidget):
    name = "bioc_R"
    description = "Bioconductor 3.7 R 3.5.1"
    priority = 1
    icon = getIconName(__file__, "bioc-r.png")
    want_main_area = False
    docker_image_name = "biodepot/bioconductor"
    docker_image_tag = "3.7__ubuntu-18.04__R-3.5.1__081318"
    inputs = [
        ("inputFile", str, "handleInputsinputFile"),
        ("Trigger", str, "handleInputsTrigger"),
    ]
    outputs = [("OutputDir", str)]
    pset = functools.partial(settings.Setting, schema_only=True)
    runMode = pset(0)
    exportGraphics = pset(False)
    runTriggers = pset([])
    triggerReady = pset({})
    inputConnectionsStore = pset({})
    optionsChecked = pset({})
    InputFile = pset(None)

    def __init__(self):
        super().__init__(self.docker_image_name, self.docker_image_tag)
        with open(getJsonName(__file__, "bioc_R")) as f:
            self.data = jsonpickle.decode(f.read())
            f.close()
        self.initVolumes()
        self.inputConnections = ConnectionDict(self.inputConnectionsStore)
        self.drawGUI()

    def handleInputsinputFile(self, value, *args):
        if args and len(args) > 0:
            self.handleInputs("inputFile", value, args[0][0], test=args[0][3])
        else:
            self.handleInputs("inputFile", value, None)

    def handleInputsTrigger(self, value, *args):
        if args and len(args) > 0:
            self.handleInputs("Trigger", value, args[0][0], test=args[0][3])
        else:
            self.handleInputs("inputFile", value, None)

    def handleOutputs(self):
        outputValue = None
        if hasattr(self, "OutputDir"):
            outputValue = getattr(self, "OutputDir")
        self.send("OutputDir", outputValue)
