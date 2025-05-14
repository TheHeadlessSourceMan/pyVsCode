import * as vscode from 'vscode';

export class MyCommand {
  static register(context: vscode.ExtensionContext) {
    let disposable = vscode.commands.registerCommand('extension.myCommand', () => {
      vscode.window.showInformationMessage('My command was executed!');
    });

    context.subscriptions.push(disposable);
  }
}