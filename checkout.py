#!/usr/bin/python3

from pathlib import Path
import shutil
import re
import os
import subprocess

def checkVersion():
    with open("RepoVivadoVersion", "r") as f:
        repoVersion = f.read().strip()
    if repoVersion == None:
        print("Unable to detect the Vivado version in use in this repository.\n")
        return False
    if not re.search("Vivado[\\\/]"+repoVersion+"[\\\/]bin;", os.environ["PATH"]):
        print("You are not running Vivado "+repoVersion+" or have not sourced the environment initialization scripts.  Aborting.\n")
        return False
    return True

def executeTcl(tclPath):
    p = subprocess.Popen(['vivado',
                          '-mode',
                          'batch',
                          '-nojournal',
                          '-nolog',
                          '-source',
                          str(tclPath)],
                         shell=True)
    p.communicate()


def main():
    if not checkVersion():
        return False

    if Path("./workspace").is_dir():
    
        if Path("./workspace.bak").is_dir():
            print("~~~ Destroying backup workspace!")
            shutil.rmtree("./workspace.bak")
            
        print("~~~ Backing up and replacing current workspace")
        shutil.move("./workspace", "./workspace.bak")

    Path("./workspace").mkdir(parents=True, exist_ok=True)

    sourcePaths = Path(".").glob("./sources/*.tcl")

    for sourcePath in sourcePaths:
        projectName = sourcePath.stem
        print("~~~ Running TCL for project: "+projectName)
        executeTcl(sourcePath)
    
if __name__ == "__main__":
    main()
