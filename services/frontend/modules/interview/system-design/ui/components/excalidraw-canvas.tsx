import dynamic from 'next/dynamic';

const ExcalidrawWrapper = dynamic(
  () => import('./excalidraw-wrapper'),
  { ssr: false }
);

export function ExcalidrawCanvas() {
  return (
    <div style={{ height: '100%', width: '100%' }}>
      <ExcalidrawWrapper />
    </div>
  );
}
