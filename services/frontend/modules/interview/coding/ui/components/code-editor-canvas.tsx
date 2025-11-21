import dynamic from "next/dynamic";
import type { editor } from "monaco-editor";

const CodeEditorWrapper = dynamic(() => import("./code-editor-wrapper"), {
  ssr: false,
});

interface CodeEditorCanvasProps {
  onEditorInit?: (editor: editor.IStandaloneCodeEditor) => void;
  initialCode?: string;
  language?: string;
  readOnly?: boolean;
}

export function CodeEditorCanvas({
  onEditorInit,
  initialCode,
  language,
  readOnly = false,
}: CodeEditorCanvasProps) {
  return (
    <div className="h-full w-full">
      <CodeEditorWrapper
        onInit={onEditorInit}
        initialCode={initialCode}
        language={language}
        readOnly={readOnly}
      />
    </div>
  );
}
