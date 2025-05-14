"""
Control an instance of Visual Studio Code using Python.

This works by starting up a visual studio code extension that acts as
a codeTools.debuggerServer server,
relaying commands and breakpoints back and forth.
"""
from codeTools.debuggerClient import RemoteDebuggerClient


class VsCodeController(RemoteDebuggerClient):
    """
    Control an instance of Visual Studio Code using Python.

    This works by starting up a visual studio code extension that acts as
    a codeTools.debuggerServer server,
    relaying commands and breakpoints back and forth.
    """


def test():
    """
    Test connecting to the vscode controller

    TODO: I have not figured out the secret sauce to make this work yet
    """
    port=45210
    vsc:VsCodeController=VsCodeController(f'http://localhost:{port}')

    def onBreakpoint(location:str):
        print(location)
        print(vsc.callStack[0].variables.get('iLogThisValue'))
        vsc.resume()

    vsc.addBreakpoint('test_target.c:320',callback=onBreakpoint)
    vsc.start()
    vsc.waitExit()
