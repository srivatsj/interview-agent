"use client";

import { useRef } from "react";
import Editor, { type OnMount } from "@monaco-editor/react";
import type { editor } from "monaco-editor";

interface CodeEditorWrapperProps {
  onInit?: (editor: editor.IStandaloneCodeEditor) => void;
  initialCode?: string;
  language?: string;
  readOnly?: boolean;
}

export default function CodeEditorWrapper({
  onInit,
  initialCode = "// Start coding here...\n",
  language = "javascript",
  readOnly = false,
}: CodeEditorWrapperProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  const handleEditorDidMount: OnMount = (editor) => {
    editorRef.current = editor;
    if (onInit) {
      onInit(editor);
    }
  };

  return (
    <div className="h-full w-full">
      <Editor
        height="100%"
        language={language}
        value={initialCode}
        onMount={handleEditorDidMount}
        theme="vs-dark"
        options={{
          minimap: { enabled: true },
          fontSize: 14,
          lineNumbers: "on",
          roundedSelection: false,
          scrollBeyondLastLine: false,
          readOnly: readOnly,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: "on",
        }}
      />
    </div>
  );
}
