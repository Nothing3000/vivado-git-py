#!/usr/bin/python3

import os
from pathlib import Path
from pathlib import PurePosixPath
from pathlib import PurePath
import shutil
import re
import subprocess
import glob

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

def generateTcl(projectPath):
    p = subprocess.Popen(['vivado', '-nojournal', '-nolog', '-mode', 'tcl', str(projectPath)],
                         stdin=subprocess.PIPE,
                         shell=True)

    commandString = "write_project_tcl -force \".exported.tcl\"\n"

    p.communicate(commandString.encode())

def processTcl(tclInFile, tclOutFile, projectName, projectPath):
    initialComments = True
    fileList = False
    commentCounter = 0
    bdPaths = sorted(Path(".").glob("workspace/*/*/*/bd"))
    blockDesignsWrapperPatterns = []
    bdWrapper = False
    workspaceSourcePath = projectPath.parent.resolve()
    targetSourcePath = Path("./sources/" + projectName)
    
    with open(tclInFile, "r") as tclIn, open(tclOutFile, "w") as tclOut:
        for line in tclIn:
            keepLine = True

            #remove initial comments
            if commentCounter == 3:
                initialComments = False
            if re.search(r"^(#\*+)",line):
               commentCounter += 1
            if initialComments:
               keepLine = False

            if re.search(r"set orig_proj_dir ",line):
                line = "set orig_proj_dir \"[file normalize \"sources/"+projectName+"\"]\""

            if re.search(r"^create_project",line):
                line = "create_project "+projectName+" workspace/"+projectName

            if re.search(r"^set obj \[get_projects \S+\]",line):
                line = "set obj [get_projects "+projectName+"]"

            if re.search(r"# 2\. The following source\(s\) files that were local or imported into the original project",line):
                fileList = True

            if fileList:
                if re.search(r"# 3. The following remote source files that were added to the original project:-",line):
                    fileList = False
                fileMatch = re.search(r"""^#\s+"(.*)"$""",line)
                if fileMatch:
                    bdMatch = re.search(r"\/bd\/(.*)\/hdl\/",line)
                    if bdMatch:
                        blockDesignsWrapperPatterns.append(re.compile(r"^set file \"hdl/"+bdMatch.group(1)+"_wrapper.vhd\"$"))
                    else:
                        filePath = Path(fileMatch.group(1))
                        interPath = filePath.resolve().relative_to(workspaceSourcePath)
                        targetPath = targetSourcePath / interPath
                        targetPath.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(filePath,targetPath)

            if re.search(r"\/workspace\/", line):
                if re.search(r"\/bd\/",line):
                    keepLine = False
                line = line.replace("/workspace/","/sources/")

            match = re.search(r"set imported_files \[import_files -fileset (\S+) ", line)
            if match:
                line = "add_files -norecurse -fileset [get_filesets "+match.group(1)+"] $files"

            for pattern in blockDesignsWrapperPatterns:
                if bdWrapper or pattern.search(line):
                    bdWrapper = True
                    keepLine = False
                    if re.search(r"^\s*$",line):
                        bdWrapper = False

            match = re.search(r"^set file_imported \[import_files -fileset (\S+) \$file\]$", line)
            if match:
                line = "add_files -norecurse -fileset [get_filesets "+match.group(1)+"] $file\n"
                            
            if keepLine:
                tclOut.write(line)

            if re.search(r"^puts \"INFO: Project created:\$project_name\"$",line):
                tclOut.write("\n")
                tclOut.write("puts \"INFO: BEGINNING TO RECONSTRUCT BLOCK DESIGN WRAPPERS\"\n")
                tclOut.write("foreach {bd_file} [glob workspace/"+projectName+"/"+projectName+".srcs/*/bd/*/*.bd] {\n")
                tclOut.write("  make_wrapper -files [get_files $bd_file] -top\n")
                tclOut.write("  }\n")
                tclOut.write("foreach {wrapper_file} [glob workspace/"+projectName+"/"+projectName+".srcs/*/bd/*/hdl/*_wrapper.vhd] {\n")
                tclOut.write("  add_files -norecurse $wrapper_file\n")
                tclOut.write("  }\n")
                tclOut.write("puts \"INFO: WRAPPERS CREATED\"\n")
                

def main():
    if not checkVersion():
        return False
    
    projectPaths = Path(".").glob("workspace/*/*.xpr")
    for projectPath in projectPaths:
        projectName = projectPath.parent.name
        sourcesPath = Path("sources/"+projectName)

        print("~~~ Processing Project: "+projectName)
        print("~~~")
        print("~~~ Exporting Project TCL from Vivado")
        
        sourcesPath.mkdir(parents=True, exist_ok=True)
        
        generateTcl(projectPath)

        print("\n~~~ Analyzing & Rewriting Project TCL and Copying source files")

        processTcl(".exported.tcl", ".processed.tcl", projectName, projectPath)

        shutil.move(".processed.tcl","./sources/"+projectName+".tcl")
        shutil.move(".exported.tcl","./sources/"+projectName+".tcl.raw")

        print("~~~")
        print("~~~ Finished processing project "+projectName)

if __name__ == "__main__":
    main()
