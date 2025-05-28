"""
Control instance of Visual Studio Code

See also:
https://code.visualstudio.com/api/references/vscode-api
"""
import typing
import os
from pathlib import Path
from paths import URLCompatible,FileLocationCompatible,FileLocation
from codeTools.codeToolsPluginInterface import (
    Ide,Breakpoint,Watchpoint,BreakpointCallback,StackFrame)
from .pythonBridgeClient import VsCode,NoVscodeInstanceException


class VsCodeProjectEditor(Ide):
    """
    Control instance of Visual Studio Code
    
    See also:
    https://code.visualstudio.com/api/references/vscode-api
    """
    def __init__(self,project:typing.Union[None,str,Path]):
        self._bridge:typing.Optional[VsCode]=None
        if project is not None:
            self.project=project

    @property
    def bridge(self)->VsCode:
        """
        Current instance of the vscode bridge.

        If there is not one connected, raises
        NoVscodeInstanceException
        """
        if self._bridge is None:
            raise NoVscodeInstanceException()
        return self._bridge

    @property
    def project(self)->typing.Optional[str]:
        """
        Project name of the project being edited
        """
        return self.bridge.instanceName
    @project.setter
    def project(self,project:typing.Union[None,str,Path]):
        self.openProject(project)

    def openProject(self,project:URLCompatible)->None:
        """
        Open a vscode directory or .workspace file
        """
        if self._bridge is None:
            self._bridge=VsCode(project)
        else:
            # TODO: untested, need to look up the api for this
            result=self.bridge.executeApi('open_workspace',project)
            print(result)

    def openCodeFile(self,location:FileLocationCompatible)->None:
        """
        Open a code file in this workspace

        UNTESTED
        """
        result=self.bridge.executeApi('openTextDocument',str(location))
        print(result)

    def read(self,location:FileLocationCompatible)->str:
        """
        Read code text from a particular file
        (NOTE: FileLocation is a range!)
        """
        # TODO: untested, need to look up the api for this
        result=self.bridge.executeApi('read',location)
        print(result)

    def write(self,location:FileLocationCompatible,data:str)->None:
        """
        Write code text to a particular file, AND SAVE.
        (NOTE: FileLocation is a range!)
        """
        # TODO: untested, need to look up the api for this
        result=self.bridge.executeApi('write',location,data)
        print(result)

    def getFiles(self)->typing.Iterable[str]:
        """
        Get the names of all files in the project

        UNTESTED
        """
        result=self._bridge.eval('textDocuments')
        print(result)

    def saveAll(self)->None:
        """
        Save all unsaved files

        UNTESTED
        """
        result=self.bridge.executeApi('saveAll',includeUntitled='false')
        print(result)

    def close(self,autosave:bool=True)->None:
        """
        Close the program
        """
        if autosave:
            self.saveAll()
        # TODO: untested, need to look up the api for this
        result=self.bridge.executeApi('close')
        print(result)

    def getDebuggedProcessPid(self)->int:
        """
        The pid of the process under test
        """
        # TODO: untested, need to look up the api for this
        result=self.bridge.executeApi('list_files')
        print(result)

    def attach(self,
        filename:typing.Optional[str]=None,
        pid:typing.Optional[int]=None,
        startIfNotRunning=False
        )->None:
        """
        Attach the debugger to a running filename or pid.

        Can raise Exception if the thing to attatch to is
        ambiguious.

        :startIfNotRunning: start the filename if there is not one running

        UNTESTED
        """
        # Look through the debug configurations to find a name like "attach"
        # Instead of this api call, it may be better to simply query the
        # .vscode/launch.json file
        debugConfigurationProvider=self.bridge.executeApi(
            'debug.currentDebugConfigurationProvider')
        name=''
        for debugConfiguration in debugConfigurationProvider['provideDebufConfigurations']():
            name=debugConfiguration.name
            if name.lower().find('attach'):
                break
        self.start(name)

    @property
    def activeDebugSession(self):
        """
        If debugger is running, return the session.
        Otherwise, raises exception.
        
        UNTESTED
        """
        result=self.bridge.executeApi('debug.activeDebugSession')
        if not result:
            raise IndexError()
        return result

    def detatch(self)->None:
        """
        Detatch the debugger from a running program.
        """
        # TODO: untested, need to look up the api for this
        result=self.activeDebugSession
        print(result)

    def start(self,sessionName:str='')->None:
        """
        start the debugger

        UNTESTED
        """
        result=self.bridge.executeApi('debug.startDebugging',
            folder='.',nameOrConfiguration=sessionName)
        print(result)

    def stop(self)->None:
        """
        stop the program

        UNTESTED
        """
        result=self.bridge.executeApi('debug.stopDebugging')
        print(result)

    def waitExit(self)->int:
        """
        wait for the application to exit
        and return the exit code
        """
        # TODO: untested, need to look up the api for this
        result=self.bridge.executeApi('list_files')
        print(result)

    def pause(self)->None:
        """
        pause the debugger
        """
        # TODO: untested, need to look up the api for this
        result=self.bridge.executeApi('list_files')
        print(result)

    def resume(self)->None:
        """
        resume the debugger
        """
        # TODO: untested, need to look up the api for this
        result=self.bridge.executeApi('list_files')
        print(result)

    def getIsPaused(self)->bool:
        """
        get whether the debugger is paused
        """
        # TODO: untested, need to look up the api for this
        result=self.bridge.executeApi('list_files')
        print(result)

    def getDebuggerLocation(self)->FileLocation:
        """
        get the current paused location
        """
        # TODO: untested, need to look up the api for this
        result=self.bridge.executeApi('list_files')
        print(result)

    def getCallStack(self)->StackFrame:
        """
        get the current call stack

        Returns the topmost stack frame
        """
        # TODO: untested, need to look up the api for this
        result=self.bridge.executeApi('list_files')
        print(result)

    def getBreakpoints(self)->typing.Generator[Breakpoint,None,None]:
        """
        get all breakpoints
        """
        # TODO: untested, need to look up the api for this
        result=self.bridge.executeApi('list_files')
        print(result)

    def addBreakpoint(self,
        location:typing.Union[str,FileLocation],
        condition:str='',
        enabled:bool=True,
        callback:typing.Optional[BreakpointCallback]=None)->None:
        """
        Add a new breakpoint

        UNTESTED
        """
        result=self.bridge.executeApi('debug.addBreakpoints',[location])
        print(result)

    def removeBreakpoint(self,
        breakpoint:Breakpoint)->None: # pylint: disable=redefined-builtin
        """
        Remove a breakpoint

        UNTESTED
        """
        result=self.bridge.executeApi('debug.removeBreakpoints',[breakpoint.name])
        print(result)

    def getWatchpoints(self)->typing.Generator[Watchpoint,None,None]:
        """
        get all watchpoints
        """
        raise NotImplementedError()

    def addWatchpoint(self,
        variable:str,
        condition:str='',
        enabled:bool=True)->Watchpoint:
        """
        Add a new watchpoint
        """
        raise NotImplementedError()

    def removeWatchpoint(self,watchpoint:Watchpoint)->None:
        """
        Remove a watchpoint
        """
        raise NotImplementedError()

    def reshapeWindow(self,
        x:typing.Optional[int]=None,
        y:typing.Optional[int]=None,
        w:typing.Optional[int]=None,
        h:typing.Optional[int]=None)->None:
        """
        Only works on Windows OS currently
        """
        if os.name=='nt':
            import win32gui
            win32gui.MoveWindow( # type: ignore
                self.bridge.hwnd,x,y,w,h,None)
    def moveWindow(self,
        x:int,
        y:int)->None:
        """
        Only works on Windows OS currently
        """
        self.reshapeWindow(x,y)
    def resizeWindow(self,
        w:int,
        h:int)->None:
        """
        Only works on Windows OS currently
        """
        self.reshapeWindow(None,None,w,h)
