import React, { useState } from 'react';
import { useStore } from '../../core/stateStore';

export function SpatialCanvas({ children }) {
  const { canvasPosition, setCanvasPosition } = useStore();
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e) => {
    // Only pan on background click, not on cards
    if (e.target.id === 'spatial-canvas-grid') {
      setIsPanning(true);
      setPanStart({ x: e.clientX - canvasPosition.x, y: e.clientY - canvasPosition.y });
    }
  };

  const handleMouseMove = (e) => {
    if (!isPanning) return;
    setCanvasPosition(e.clientX - panStart.x, e.clientY - panStart.y, canvasPosition.scale);
  };

  const handleMouseUp = () => {
    setIsPanning(false);
  };

  const handleWheel = (e) => {
    const scaleFactor = e.deltaY < 0 ? 1.05 : 0.95;
    const newScale = Math.min(Math.max(canvasPosition.scale * scaleFactor, 0.4), 2.0);
    setCanvasPosition(canvasPosition.x, canvasPosition.y, newScale);
  };

  return (
    <div
      id="spatial-canvas-grid"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
      className="absolute inset-0 overflow-hidden cursor-grab active:cursor-grabbing bg-zinc-950 select-none"
      style={{
        backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 0)',
        backgroundSize: '30px 30px',
        backgroundPosition: `${canvasPosition.x}px ${canvasPosition.y}px`
      }}
    >
      <div
        className="absolute origin-top-left transition-transform duration-75 ease-out"
        style={{
          transform: `translate(${canvasPosition.x}px, ${canvasPosition.y}px) scale(${canvasPosition.scale})`
        }}
      >
        {children}
      </div>
    </div>
  );
}
