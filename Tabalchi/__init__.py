#For creating package
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("Tabalchi")
except PackageNotFoundError:
    __version__ = "Please install Tabalchi with setup.py"

#Package Modules
from .main import*
