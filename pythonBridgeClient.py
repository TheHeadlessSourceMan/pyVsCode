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
import json
from pathlib import Path
import psutil
import websocket # type: ignore


JsonLike=typing.Dict[str,typing.Any]


class Remote:
    """
    Base class for something on the remote side
    """
    def __init__(self,
        vsCode:"VsCode",
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
        vsCode:"VsCode",
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
        vsCode:"VsCode",
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

    def __init__(self,vscode:"VsCode",commandName:str):
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
        vsCode:"VsCode",
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


class VsCode:
    """
    Access visual studio code api via websocket

    See:
        https://code.visualstudio.com/api/references/vscode-api
    """
    _apiFunctions:typing.List[str]=[]
    _commands:typing.Dict[str,CommandCaller]={}

    def __init__(self,
        instanceName:typing.Optional[str]=None,
        host:typing.Optional[str]=None,
        port:typing.Union[None,int,str]=None,
        ):
        self._instanceName=instanceName
        if instanceName is not None:
            instance=self.getInstanceInfo(instanceName)
            if instance is None:
                msg=[f'No vs code instance called "{instanceName}" in:']
                for instance in self.getInstances().values():
                    msg.append(str(instance))
                raise IndexError('\n\t'.join(msg))
            host=instance.get('host',host)
            port=instance.get('port',port)
        if host is None:
            host='localhost'
        self._host=host
        if port is None:
            raise Exception("Unable to assign network port")
        self._port=int(port)
        self._websocket:typing.Optional[websocket.WebSocket]=None
        self.queryApi(False)

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
        jsonData=filename.read_text('utf-8',errors='ignore')
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
        instanceName:str
        )->typing.Optional[JsonLike]:
        """
        Get a specific vscode instance
        """
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
        *args:typing.Any
        )->typing.Dict[str,typing.Any]:
        """
        Execute a vscode api.

        See:
            https://code.visualstudio.com/api/references/vscode-api

        returns json
        """
        jsonStr:str=json.dumps({
            "command":functionName,
            "args":args
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
