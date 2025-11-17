"use client";

import { Excalidraw } from "@excalidraw/excalidraw";
import "@excalidraw/excalidraw/index.css";

interface ReadonlyExcalidrawProps {
  elements: readonly unknown[];
  appState?: Record<string, unknown>;
}

export const ReadonlyExcalidraw = ({
  elements,
  appState,
}: ReadonlyExcalidrawProps) => {
  // Provide default appState structure that Excalidraw expects
  const defaultAppState = {
    viewBackgroundColor: "#ffffff",
    currentItemStrokeColor: "#000000",
    currentItemBackgroundColor: "transparent",
    currentItemFillStyle: "hachure",
    currentItemStrokeWidth: 1,
    currentItemStrokeStyle: "solid",
    currentItemRoughness: 1,
    currentItemOpacity: 100,
    currentItemFontFamily: 1,
    currentItemFontSize: 20,
    currentItemTextAlign: "left",
    currentItemStartArrowhead: null,
    currentItemEndArrowhead: "arrow",
    scrollX: 0,
    scrollY: 0,
    zoom: { value: 1 },
    currentItemRoundness: "round",
    gridSize: null,
    colorPalette: {},
    collaborators: new Map(), // ✅ Fix for collaborators.forEach error
  };

  // Merge appState but ensure collaborators is always a Map
  const mergedAppState = {
    ...defaultAppState,
    ...appState,
    collaborators: new Map(), // Always use empty Map for read-only view
  };

  return (
    <div style={{ height: "100%", width: "100%" }}>
      <Excalidraw
        theme="light"
        viewModeEnabled={true}
        zenModeEnabled={false}
        gridModeEnabled={false}
        initialData={{
          elements: (elements || []) as never,
          appState: mergedAppState as never,
        }}
      />
    </div>
  );
};
