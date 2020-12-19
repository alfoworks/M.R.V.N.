import sys
import os
import importlib

from typing import List
from discord import *
from config import Config

client = Client()

def main(args: List[str]):
    sys.path.append(os.path.join(os.getcwd(), Config.modules_dir))
    for file in os.listdir(Config.modules_dir):
        if os.path.isdir(os.path.join(Config.modules_dir, file)):
            module = importlib.import_module(file)


if __name__ == '__main__':
    main(sys.argv)