"""
Manage vscode extensions
"""
import typing
import os
import shutil
import json
import uuid as u
from stringTools import Version


DEFAULT_VSCODE_EXTENSION_DIR=os.path.expandvars(
    r'%USERPROFILE%\.vscode\extensions\extensions.json')

class VsCodeExtension:
    """
    Information about a single extension in vs code
    """
    def __init__(self,jsonData:typing.Optional[str|typing.Dict]=None):
        self._jsonObj:typing.Dict={}
        if jsonData:
            self.json=jsonData # type:ignore

    @property
    def json(self)->str:
        """
        Get this as a JSON string
        """
        return json.dumps(self.jsonObj)
    @json.setter
    def json(self,jsonData:typing.Union[str,typing.Dict]):
        if isinstance(jsonData,str):
            self.jsonObj=json.loads(jsonData)
        else:
            self.jsonObj=jsonData

    @property
    def jsonObj(self):
        """
        Get this as a JSON-compatible object
        """
        return self._jsonObj
    @jsonObj.setter
    def jsonObj(self,jsonObj):
        self._jsonObj=jsonObj

    @property
    def id(self)->str:
        """
        id of this extension
        """
        return self._jsonObj["identifier"]["id"]

    @property
    def name(self)->str:
        """
        name of this extension
        """
        return self.id.split('.',1)[-1]

    @property
    def company(self)->str:
        """
        provider of this extension
        """
        return self.id.split('.',1)[0]

    @property
    def version(self)->Version:
        """
        version of this extension
        """
        return Version(self._jsonObj["version"])


class VsCodeExtensions:
    """
    Manage vscode extensions

    JSON example:
    {
        "identifier":{
            "id":"atlassian.atlascode",
            "uuid":"ede0d8fe-2180-4cf5-85f5-075dc43d4b8f"
        },
        "version":"3.0.6",
        "location":{
            "$mid":1,
            "fsPath":"c:\\Users\\carl\\.vscode\\extensions\\atlassian.atlascode-3.0.6",
            "_sep":1,
            "external":"file:///c%3A/Users/carl/.vscode/extensions/atlassian.atlascode-3.0.6",
            "path":"/c:/Users/carl/.vscode/extensions/atlassian.atlascode-3.0.6",
            "scheme":"file"
        },
        "relativeLocation":"atlassian.atlascode-3.0.6",
        "metadata":{
            "id":"ede0d8fe-2180-4cf5-85f5-075dc43d4b8f",
            "publisherId":"bfee309e-1e6f-4488-b27e-f29e6e2ad2f2",
            "publisherDisplayName":"Atlassian",
            "targetPlatform":"undefined",
            "isApplicationScoped":false,
            "updated":true,
            "isPreReleaseVersion":false,
            "installedTimestamp":1694793618281,
            "preRelease":false
        }
    }
    """

    def __init__(self,pathToJson:typing.Optional[str]=None):
        self._jsonData:typing.Any=None
        if pathToJson is None:
            # TODO: only works on windows
            pathToJson=DEFAULT_VSCODE_EXTENSION_DIR
        self.pathToJson=pathToJson

    def load(self,force=True):
        """
        Will be called automatically.
        Only needs to be called manually to force a reload.
        """
        if force or self._jsonData is None:
            f=open(self.pathToJson,'rb')
            data=f.read()
            self._jsonData=json.loads(data)

    def installed(self)->typing.Generator[VsCodeExtension,None,None]:
        """
        Returns id, version of all installed extensions
        """
        self.load(False)
        for extension in self._jsonData:
            yield VsCodeExtension(extension)

    def add(self,extension:VsCodeExtension)->None:
        """
        Add a new extension to the list if it's not already there
        """
        result=[]
        for current in self.installed():
            if current.id!=extension.id:
                result.append(current)
        result.append(extension)


def addExtension(
    extensionId:str,
    copyFilesFrom:str,
    version:typing.Optional[str]=None,
    uuid:typing.Union[None,u.UUID,str]=None):
    """
    Create and install an extension
    """
    if version is None:
        version="1.0.0"
    if uuid is None:
        # generate one on the fly
        uuid=u.uuid1()
    elif not isinstance(uuid,str):
        uuid=str(uuid)
    ext:typing.Dict[str,typing.Any]={}
    ext["identifier"]={"id":extensionId,"uuid":uuid}
    ext["version"]=version
    relativeDir=f"{extensionId}-{version}"
    extDir=os.sep.join((DEFAULT_VSCODE_EXTENSION_DIR,))
    extDirRoot='/'+extDir.replace(os.sep,'/')
    estUrl="file://"+extDirRoot.replace(':','%3A')
    ext["location"]={
        "$mid":1,
        "fsPath":extDir,
        "_sep":1,
        "external":estUrl,
        "path":extDirRoot,
        "scheme":"file"
    }
    ext["relativeLocation"]=relativeDir
    copyFilesFrom=os.path.abspath(copyFilesFrom)
    copyFilesTo=os.path.abspath(
        os.path.join(DEFAULT_VSCODE_EXTENSION_DIR,ext[relativeDir]))
    shutil.copytree(copyFilesFrom,copyFilesTo,symlinks=True,dirs_exist_ok=True)


for ext in VsCodeExtensions().installed():
    print(f'{ext.name}\t\t{ext.version}')
