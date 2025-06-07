"""
Access visual studio code api via websocket

This requires the python-vscode-bridge vscode
plugin to be installed and running.

You can get it here:
    https://github.com/TheHeadlessSourceMan/vscode-python-bridge

See:
    https://code.visualstudio.com/api/references/vscode-api
"""
import typing
import os
import json
from pathlib import Path
from codeTools.codeToolsPluginInterface import pidToHwnds
import psutil
import websocket # type: ignore


JsonLike=typing.Dict[str,typing.Any]

class NoVscodeInstanceException(Exception):
    """
    Exception for when we want to do something on a vscode instance
    but there is not one attached.
    """
    def __init__(self,instanceName:typing.Optional[str]=None):
        msg='No VsCode instance connected'
        if instanceName is not None and instanceName:
            msg=f'No VsCode instance named "{instanceName}" connected'
        Exception.__init__(self,msg)

class Remote:
    """
    Base class for something on the remote side
    """
    def __init__(self,
        vsCode:"VsCodeBridgeClient",
        parent:typing.Optional["Remote"],
        name:str):
        """ """
        self.vsCode=vsCode
        self.name=name
        self.parent=parent

    @property
    def children(self)->typing.Iterable["Remote"]:
        """
        All children for this item
        """
        return []

    @property
    def fullPath(self)->str:
        """
        Full path to this item
        """
        if self.parent is None:
            return self.name
        return f'{self.parent.fullPath}.{self.name}'

    def treeWalk(self)->typing.Generator['Remote',None,None]:
        """
        Breadth-first traversal.
        """
        yield from self.children
        for child in self.children:
            yield from child.treeWalk()

    def __dict__(self)->typing.Dict[str,"Remote"]: # type: ignore
        ret:typing.Dict[str,"Remote"]={}
        for child in self.children:
            ret[child.name]=child
        return ret


class RemoteObject(Remote):
    """
    Remote object
    """
    def __init__(self,
        vsCode:"VsCodeBridgeClient",
        parent:typing.Optional["Remote"],
        name:str):
        """ """
        Remote.__init__(self,vsCode,parent,name)

    @property
    def children(self)->typing.Iterable["Remote"]:
        """
        All children for this item
        """
        for child in self.vsCode.inspect(self.fullPath).values():
            if child['type']=='object':
                yield RemoteObject(
                    self.vsCode,self,child['name'])
            elif child['type']=='function':
                yield RemoteFunction(
                    self.vsCode,self,child['name'],child['params'])
            else:
                yield RemoteValue(
                    self.vsCode,self,child['name'])

    def __dict__(self)->JsonLike: # type: ignore
        return self.vsCode.inspect(self.fullPath)

    def __repr__(self,
        indent:str="",
        recursive:bool=False):
        """ """
        ret=[f'{indent}object {self.name}']
        nextIndent=f'{indent}\t'
        for child in self.children:
            if isinstance(child,RemoteObject):
                if not recursive:
                    ret.append(f'{nextIndent}object {child.name}')
                else:
                    ret.append(child.__repr__(nextIndent,recursive))
            else:
                ret.append(child.__repr__(nextIndent)) # type: ignore
        return '\n'.join(ret)


class RemoteValue(Remote):
    """
    Remote value
    """
    def __init__(self,
        vsCode:"VsCodeBridgeClient",
        parent:typing.Optional["Remote"],
        name:str):
        """ """
        Remote.__init__(self,vsCode,parent,name)

    def set(self,value:typing.Any)->JsonLike:
        """
        Set the remote value
        """
        return self.vsCode.eval(f"{self.fullPath}={value};")

    def get(self)->JsonLike:
        """
        Get the remote value
        """
        return self.vsCode.eval(f"{self.fullPath};")

    def __repr__(self,indent:str='')->str:
        """ """
        return f"{indent}{self.name}"


class CommandCaller:
    """
    Helper object that converts a command name
    into a proper callable
    """

    def __init__(self,vscode:"VsCodeBridgeClient",commandName:str):
        """
        """
        self.vscode=vscode
        self.commandName=commandName

    def __call__(self,
        *args:typing.Any,
        **kwargs:typing.Any,
        )->JsonLike:
        """
        execute the command
        """
        return self.vscode.executeCommand(self.commandName,*args,**kwargs)


class RemoteFunction(Remote):
    """
    Callable remote function
    """
    def __init__(self,
        vsCode:"VsCodeBridgeClient",
        parent:typing.Optional["Remote"],
        name:str,
        parameters:typing.List[str]):
        """ """
        Remote.__init__(self,vsCode,parent,name)
        self.parameters=parameters

    def call(self,
        *args # type: ignore
        )->JsonLike:
        """
        Call the function
        """
        encodedArgs:typing.List[str]=[]
        for arg in args: # type: ignore
            if isinstance(arg,str):
                arg='"'+(arg.replace('\\','\\\\').replace('"','\\"'))+'"'
            else:
                arg=str(arg) # type: ignore
            encodedArgs.append(arg)
        argStr=', '.join(encodedArgs)
        return self.vsCode.eval(f'{self.fullPath}({argStr});')
    __call__=call # type: ignore

    def __repr__(self,indent:str='')->str:
        """ """
        params=', '.join(self.parameters)
        return f'{indent}def {self.name}({params})'


class VsCodeBridgeClient:
    """
    Access visual studio code api via websocket

    See:
        https://code.visualstudio.com/api/references/vscode-api
    """
    _apiFunctions:typing.List[str]=[]
    _commands:typing.Dict[str,CommandCaller]={}

    def __init__(self,
        instanceName:typing.Union[None,str,Path]=None,
        createNewInstance:bool=False,
        createInstanceIfMissing:bool=True,
        host:typing.Optional[str]=None,
        port:typing.Union[None,int,str]=None,
        ):
        if instanceName is not None:
            if isinstance(instanceName,str):
                instanceName=Path(os.path.expandvars(instanceName))
            instanceName=instanceName.absolute()
        self._instanceName:typing.Optional[Path]=instanceName
        self._instanceInfo:typing.Optional[JsonLike]=None
        if instanceName is not None:
            if not createNewInstance:
                self._instanceInfo=self.getInstanceInfo(instanceName)
                if self._instanceInfo is None:
                    msg=[f'No vs code instance named "{instanceName}" in:']
                    for instance in self.getInstances().values():
                        msg.append(str(instance))
                    raise IndexError('\n\t'.join(msg))
                else:
                    createNewInstance=createInstanceIfMissing
            if createNewInstance:
                self.createNewInstance(instanceName)
            host=self._instanceInfo.get('host',host)
            port=self._instanceInfo.get('port',port)
        if host is None:
            host='localhost'
        self._instanceInfo['host']=host
        self._instanceInfo['port']=int(port)
        self._websocket:typing.Optional[websocket.WebSocket]=None
        self.queryApi(False)

    @classmethod
    def createNewInstance(cls,
        instanceName:typing.Union[None,str,Path]=None
        )->JsonLike:
        """
        Create a new visual studio code program instance

        :instanceName: aka, the location of the directory or .workspace file
        """
        import time
        import subprocess
        if instanceName is None:
            instanceName=""
        cmd=['code',instanceName]
        po=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        _,err=po.communicate()
        err=err.strip()
        if err:
            raise Exception(err.decode('utf-8',errors='ignore'))
        pid=po.pid
        for _ in range(50):
            time.sleep(0.10)
            instances=cls.getInstances()
            instance=instances.get(pid)
            if instance is not None:
                return instance
        msg="""Unable to find instance we started
        (is the bridge plugin installed?)"""
        raise Exception(msg)

    @classmethod
    def getInstances(cls)->JsonLike:
        """
        Returns local instances, tracked in ~/.vscode_instances.json

        The format is:
        [
            1234={
                "name":"~/myProgram",
                "host":"localhost",
                "port":8180,
                "pid":1234,
                "hwnd":5678
            },
            ...
        ]
        """
        filename=Path().home()/'.vscode_instances.json'
        try:
            jsonData=filename.read_text('utf-8',errors='ignore')
        except FileNotFoundError:
            return {}
        instances:typing.Dict[str,JsonLike]=json.loads(jsonData)
        # check which instances are a valid process id
        validInstances:JsonLike={}
        for pid,instance in instances.items():
            if psutil.pid_exists(int(pid)):
                validInstances[pid]=instance
        if len(instances)!=len(validInstances):
            # update the file to remove old instances
            jsonData=json.dumps(validInstances)
            filename.write_text(jsonData,'utf-8',errors='ignore')
        return validInstances

    @classmethod
    def findInstance(cls,instanceName:str)->typing.Optional[JsonLike]:
        """
        Find an instance by name
        """
        instances=cls.getInstances().values()
        for instance in instances:
            if instance['name']==instanceName:
                return instance
        return None

    @property
    def localInstances(self)->JsonLike:
        """
        Get all of the local instances of vscode
        """
        return self.getInstances()
    instances=localInstances

    @classmethod
    def getInstanceInfo(cls,
        instanceName:typing.Union[str,Path]
        )->typing.Optional[JsonLike]:
        """
        Get a specific vscode instance
        """
        if isinstance(instanceName,Path):
            instanceName=str(instanceName)
        for instance in cls.getInstances().values():
            if instance['name']==instanceName:
                return instance
        return None

    @property
    def host(self)->str:
        """
        host of the vscode instance
        """
        return self._host
    @host.setter
    def host(self,host:str):
        self._host=host
        self._websocket=None

    @property
    def port(self)->int:
        """
        port of the vscode instance
        """
        return self._port
    @port.setter
    def port(self,port:typing.Union[str,int]):
        self._port=int(port)
        self._websocket=None

    @property
    def instanceName(self)->str:
        """
        name of the vscode instance
        """
        if self._instanceName is None:
            return ''
        return self._instanceName
    @instanceName.setter
    def instanceName(self,instanceName:typing.Optional[str]):
        if instanceName is not None:
            instance=self.findInstance(instanceName)
            if instance is None:
                raise IndexError(
                    f'No vs code instance called "{instanceName}"')
            self.host=instance.get('host','localhost')
            self.port=instance.get('port',8180)
        self._instanceName=instanceName

    def __del__(self):
        self.closeSocket()

    def kill(self)->None:
        """
        If things get out of hand, kill vscode entirely
        """
        os.kill(self.pid)

    @property
    def instanceInfo(self)->JsonLike:
        """
        Information about the current instance from the file

        Can raise an exception if the instance was not specified,
        does not exist, or the process has disappeared.
        """
        if self._instanceInfo is None \
            or not psutil.pid_exists(int(self._instanceInfo['pid'])):
            raise NoVscodeInstanceException(self._instanceName)
        return self._instanceInfo

    @property
    def pid(self)->int:
        """
        System process id for this instance
        of visual studio code
        """
        return int(self.instanceInfo['pid'])

    @property
    def hwnds(self)->typing.Iterable[str]:
        """
        All of the top-level windows associated
        with this vscode instance
        """
        hwnds=pidToHwnds(self.pid)
        return hwnds

    @property
    def hwnd(self)->str:
        """
        Window handle of the vscode instance
        """
        hwnd=self.instanceInfo.get('hwnd')
        if hwnd is None:
            hwnds=self.hwnds
            if hwnds:
                hwnd=hwnds[0]
                self.instanceInfo['hwnd']=hwnd
        return hwnd

    def getCommands(self,
        force:bool=True
        )->typing.Dict[str,CommandCaller]:
        """
        (re)get list of commands
        """
        if force or not self._commands:
            self._commands={}
            ret=self.executeApi('getCommands')
            for commandName in ret:
                self._commands[commandName]=\
                    CommandCaller(self,commandName)
        return self._commands

    @property
    def commands(self
        )->typing.Dict[str,CommandCaller]:
        """
        All available commands
        """
        return self.getCommands(False)

    def openSocket(self,force:bool=False)->websocket.WebSocket:
        """
        Open, or re-open a websocket.

        Generally, no need to call this yourself. It will be
        called automatically as needed.
        """
        if force:
            self.closeSocket()
        if self._websocket is None:
            self._websocket=websocket.create_connection( # type: ignore
                f"ws://{self._host}:{self._port}")
        return self._websocket
    @property
    def websocket(self)->websocket.WebSocket:
        """
        Get the websocket in use.  Open if necessary.
        """
        return self.openSocket()

    def closeSocket(self):
        """
        Close the websocket
        """
        if self._websocket is not None:
            self._websocket.close()
            self._websocket=None

    def queryApi(self,force:bool=True)->typing.List[str]:
        """
        Query what is available on the remote vscode api
        (this is called automatically as needed)
        """
        if not self._apiFunctions or force:
            self._apiFunctions=[]
            result=self.executeApi("queryApi","vscode")
            for apiName in result["members"]:
                self._apiFunctions.append(apiName)
        return self._apiFunctions

    def eval(self,jsString:str)->typing.Dict[str,typing.Any]:
        """
        Execute remote javascript and return the result
        """
        return self.executeApi("eval",jsString)

    def inspect(self,
        valueName:typing.Optional[str]=None
        )->typing.Dict[str,typing.Any]:
        """
        Inspect remote javascript and return the result
        """
        if valueName:
            ret=self.executeApi("inspect",valueName)
        else:
            ret=self.executeApi("inspect")
        if ret['status']=='OK':
            return ret['members']
        raise Exception(str(ret))

    def executeApi(self,
        functionName:str,
        *args:typing.Any,
        **kwargs:typing.Any
        )->typing.Dict[str,typing.Any]:
        """
        Execute a vscode api.

        See:
            https://code.visualstudio.com/api/references/vscode-api

        returns json
        """
        jsonStr:str=json.dumps({
            "command":functionName,
            "args":args,
            "kwargs":kwargs
            })
        self.websocket.send(jsonStr) # type: ignore
        jsonStr=self.websocket.recv() # type: ignore
        try:
            jsonObj=json.loads(jsonStr) # type: ignore
        except Exception as e:
            print(jsonStr) # type: ignore
            raise e
        return jsonObj

    def executeCommand(self,
        commandName:str,
        *args:typing.Any,
        **kwargs:typing.Any,
        )->JsonLike:
        """
        Execute a command (like from the vscode ctrl+shift+p menu)
        returns json
        """
        argsList=list(args) # type: ignore
        argsList.insert(0,commandName)
        jsonData:str=json.dumps({
            "command":"executeCommand",
            "args":args,
            "kwargs":kwargs
            })
        jsonData=self.websocket.send(jsonData) # type: ignore
        return json.loads(jsonData)
