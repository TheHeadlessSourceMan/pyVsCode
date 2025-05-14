import { MyCommand } from './myCommand';

export function registerCommands(context: vscode.ExtensionContext) {
  MyCommand.register(context);
}