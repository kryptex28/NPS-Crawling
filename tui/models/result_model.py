import subprocess
import sys

class ResultModel():

    def __init__(self) -> None:
        pass

    def open(self):
        path = ""

        if sys.platform == "win32":
            subprocess.Popen(["start", path], shell=True)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])