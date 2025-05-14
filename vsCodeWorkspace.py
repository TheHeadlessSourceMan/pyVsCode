"""
Tools for managing visual studio code workspaces
"""
import typing
import os
import shutil


def createVscodeWorkspace(
    location:str,
    basedOn:str=r"D:\python\data\editor_settings_defaults",
    additionalFolders:typing.Iterable[str]=('.',)):
    """
    Create a new vscode workspace
    """
    shutil.copytree(basedOn,location)
    folderList=set(additionalFolders)
    folderList.add('.')
    folders=[]
    for folder in folderList:
        folder='{ "path": "'+folder+'" }'
    jsondata="""{
        "folders": [
            """+(',\n\t'.join(folders))+"""
        ],
        "settings": {
            "window.title": "${folderName}"
        }
    }"""
    workspaceFilename=os.sep.join((
        location,
        location.rsplit(os.sep,1)[-1].split('.',1)[0]+'.code-workspace'))
    with open(workspaceFilename,'w',encoding="utf-8") as f:
        f.write(jsondata)
