// This is a web extension that runs in the browser
const vscode = require('vscode');
const http = require('http');

// This is the entry point for the extension
function activate(context) {
  // Create a web server that listens on port 8080
  const server = http.createServer((req, res) => {
    // Parse the request URL
    const url = new URL(req.url, `http://${req.headers.host}`);
    // Handle different paths
    if (url.pathname === '/') {
      // Send a welcome message
      res.writeHead(200, {'Content-Type': 'text/plain'});
      res.end('Hello from VS Code Server!\n');
    } else if (url.pathname === '/launch') {
      // Get the launch target from the query parameter
      const target = url.searchParams.get('target');
      if (target) {
        // Execute the launch command with the target as argument
        vscode.commands.executeCommand('workbench.action.debug.selectandstart', target)
          .then(() => {
            // Send a success message
            res.writeHead(200, {'Content-Type': 'text/plain'});
            res.end(`Launched ${target} successfully!\n`);
          })
          .catch((error) => {
            // Send an error message
            res.writeHead(500, {'Content-Type': 'text/plain'});
            res.end(`Failed to launch ${target}: ${error}\n`);
          });
      } else {
        // Send a bad request message
        res.writeHead(400, {'Content-Type': 'text/plain'});
        res.end('Missing target parameter\n');
      }
    } else if (url.pathname === '/breakpoints') {
      // Get the action from the query parameter
      const action = url.searchParams.get('action');
      if (action === 'list') {
        // Get the breakpoints from the debug session
        const breakpoints = vscode.debug.breakpoints;
        // Send a JSON array of breakpoints
        res.writeHead(200, {'Content-Type': 'application/json'});
        res.end(JSON.stringify(breakpoints));
      } else if (action === 'set') {
        // Get the file and line from the query parameters
        const file = url.searchParams.get('file');
        const line = parseInt(url.searchParams.get('line'));
        const callback = url.searchParams.get('callback'); // get the callback url parameter
        if (file && line && callback) {
          // Create a source breakpoint at the given file and line
          const breakpoint = new vscode.SourceBreakpoint(new vscode.Location(vscode.Uri.file(file), new vscode.Position(line - 1, 0)));
          // Add the breakpoint to the debug session
          vscode.debug.addBreakpoints([breakpoint]);
          // Register a listener for breakpoint events
          context.subscriptions.push(vscode.debug.onDidChangeBreakpoints(event => {
            // Check if the breakpoint was hit
            if (event.session && event.session.state === 'stopped' && event.session.configuration.name === 'Launch Program') {
              // Get the current stack frame of the debug session
              event.session.customRequest('stackTrace', { threadId: event.session.state.reason.threadId })
                .then(stackTrace => {
                  // Check if the stack frame matches the breakpoint location
                  if (stackTrace.stackFrames[0].source.path === file && stackTrace.stackFrames[0].line === line) {
                    // Replace the {location} placeholder with the actual location in the callback url
                    const location = `${file}:${line}`;
                    const replacedCallback = callback.replace('{location}', location);
                    // Make an HTTP request to the callback url
                    http.get(replacedCallback, response => {
                      console.log(`Called ${replacedCallback} with status code ${response.statusCode}`);
                    }).on('error', error => {
                      console.error(`Failed to call ${replacedCallback}: ${error.message}`);
                    });
                  }
                })
                .catch(error => {
                  console.error(`Failed to get stack trace: ${error.message}`);
                });
            }
          }));
          // Send a success message
          res.writeHead(200, {'Content-Type': 'text/plain'});
          res.end(`Set breakpoint at ${file}:${line} with callback ${callback}\n`);
        } else {
          // Send a bad request message
          res.writeHead(400, {'Content-Type': 'text/plain'});
          res.end('Missing file, line or callback parameter\n');
        }
      } else if (action === 'modify') {
        // Get the file and line from the query parameters
        const file = url.searchParams.get('file');
        const line = parseInt(url.searchParams.get('line'));
        if (file && line) {
          // Find the breakpoint at the given file and line
          const breakpoint = vscode.debug.breakpoints.find(b => b instanceof vscode.SourceBreakpoint && b.location.uri.fsPath === file && b.location.range.start.line === line - 1);
          if (breakpoint) {
            // Modify the breakpoint properties as needed
            breakpoint.enabled = !breakpoint.enabled; // toggle enabled state
            breakpoint.condition = 'x > 10'; // set a condition
            breakpoint.logMessage = 'Breakpoint hit'; // set a log message
            // Update the breakpoint in the debug session
            vscode.debug.removeBreakpoints([breakpoint]);
            vscode.debug.addBreakpoints([breakpoint]);
            // Send a success message
            res.writeHead(200, {'Content-Type': 'text/plain'});
            res.end(`Modified breakpoint at ${file}:${line}\n`);
          } else {
            // Send a not found message
            res.writeHead(404, {'Content-Type': 'text/plain'});
            res.end(`No breakpoint found at ${file}:${line}\n`);
          }
        } else {
          // Send a bad request message
          res.writeHead(400, {'Content-Type': 'text/plain'});
          res.end('Missing file or line parameter\n');
        }
      } else {
        // Send a bad request message
        res.writeHead(400, {'Content-Type': 'text/plain'});
        res.end('Missing or invalid action parameter\n');
      }
    } else {
      // Send a not found message
      res.writeHead(404, {'Content-Type': 'text/plain'});
      res.end('Not found\n');
    }
  });

  // Start the server
  server.listen(45210, () => {
    console.log('Server running at http://localhost:45210/');
  });

  // Register a disposable to stop the server when the extension is deactivated
  context.subscriptions.push({
    dispose: () => {
      server.close();
    }
  });
}

// Export the activate function
exports.activate = activate;
