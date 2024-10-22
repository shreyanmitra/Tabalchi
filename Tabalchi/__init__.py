#For creating package
from pkg_resources import get_distribution, DistributionNotFound

try:
    dist = get_distribution("Tabalchi")
except DistributionNotFound:
    __version__ = "Please install Tabalchi with setup.py"
else:
    __version__ = dist.version

#Package Modules
from .main import*
