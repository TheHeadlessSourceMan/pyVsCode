import * as assert from 'assert';
import * as vscode from 'vscode';
import * as myExtension from '../../extension';

suite('Extension Test Suite', () => {
  vscode.window.showInformationMessage('Start all tests.');

  test('Sample test', () => {
    assert.strictEqual(-1, [1, 2, 3].indexOf(4));
  });

  test('Activation test', async () => {
    const extension = vscode.extensions.getExtension('myExtension.sample-extension');
    if (!extension) {
      assert.fail('Extension not found.');
    }

    await extension.activate();
    assert.ok(true);
  });
});