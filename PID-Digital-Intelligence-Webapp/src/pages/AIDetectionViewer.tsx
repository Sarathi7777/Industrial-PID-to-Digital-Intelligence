import React, { useState, useEffect } from "react";
import {
  Eye,
  Loader2,
  AlertCircle,
  X,
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from "lucide-react";
import { getDetectionImage } from "../Service/yoloDetectionService";

const AIDetectionViewer = ({ results, isOpen, onClose }) => {
  const [imageUrl, setImageUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (isOpen && results?.symbol_image_url) {
      fetchDetectionImage();
    }
  }, [isOpen, results]);

  const fetchDetectionImage = async () => {
    if (!results?.symbol_image_url) return;

    setLoading(true);
    setError(null);

    try {
      const blob = await getDetectionImage(results.symbol_image_url);
      const url = URL.createObjectURL(blob);
      setImageUrl(url);
    } catch (err) {
      console.error("Error fetching detection image:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (imageUrl) {
      URL.revokeObjectURL(imageUrl);
      setImageUrl(null);
    }
    setZoom(1);
    setPosition({ x: 0, y: 0 });
    setError(null);
    onClose();
  };

  const handleZoomIn = () => {
    setZoom((prev) => Math.min(prev * 1.2, 5));
  };

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(prev / 1.2, 0.2));
  };

  const handleReset = () => {
    setZoom(1);
    setPosition({ x: 0, y: 0 });
  };

  const handleMouseDown = (e) => {
    if (zoom > 1) {
      setIsDragging(true);
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y,
      });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging && zoom > 1) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-6xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full flex items-center justify-center">
              <Eye className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">
                AI Detection Results
              </h2>
              <p className="text-slate-400 text-sm">
                Detected symbols and components visualization
              </p>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center space-x-2">
            {imageUrl && (
              <>
                <button
                  onClick={handleZoomOut}
                  className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <span className="text-slate-400 text-sm min-w-[60px] text-center">
                  {Math.round(zoom * 100)}%
                </span>
                <button
                  onClick={handleZoomIn}
                  className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
                  title="Zoom In"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button
                  onClick={handleReset}
                  className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
                  title="Reset View"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              </>
            )}
            <button
              onClick={handleClose}
              className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {loading && (
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <Loader2 className="w-12 h-12 text-cyan-400 animate-spin mx-auto mb-4" />
                <p className="text-slate-300">
                  Loading AI detection results...
                </p>
                <p className="text-slate-500 text-sm mt-1">
                  Fetching annotated image from server
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                <p className="text-red-400 font-medium">
                  Failed to load detection image
                </p>
                <p className="text-slate-500 text-sm mt-1">{error}</p>
                <button
                  onClick={fetchDetectionImage}
                  className="mt-4 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}

          {imageUrl && !loading && !error && (
            <div className="bg-slate-900/50 rounded-lg overflow-hidden">
              <div
                className="relative overflow-hidden h-[600px] cursor-move"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
              >
                <img
                  src={imageUrl}
                  alt="AI Detection Results"
                  className="absolute inset-0 w-full h-full object-contain transition-transform duration-200"
                  style={{
                    transform: `scale(${zoom}) translate(${
                      position.x / zoom
                    }px, ${position.y / zoom}px)`,
                    cursor: isDragging
                      ? "grabbing"
                      : zoom > 1
                      ? "grab"
                      : "default",
                  }}
                  draggable={false}
                />
              </div>

              {/* Image Info */}
              <div className="p-4 border-t border-slate-700 bg-slate-800/50">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-slate-400">Components Detected:</span>
                    <span className="text-white ml-2">
                      {results?.metadata?.summary?.component_count || 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">Connections:</span>
                    <span className="text-white ml-2">
                      {results?.metadata?.summary?.connection_count || 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">Avg Confidence:</span>
                    <span className="text-cyan-400 ml-2">
                      {results?.metadata?.quality_metrics
                        ?.avg_detection_confidence
                        ? `${(
                            results.metadata.quality_metrics
                              .avg_detection_confidence * 100
                          ).toFixed(1)}%`
                        : "N/A"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">Processing Time:</span>
                    <span className="text-white ml-2">
                      {results?.metadata?.timings_ms?.total || 0}ms
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {!results?.symbol_image_url && !loading && !error && (
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <AlertCircle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
                <p className="text-slate-300">No detection image available</p>
                <p className="text-slate-500 text-sm mt-1">
                  The analysis results don't include a symbol image URL
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Demo component to show how to integrate
const AIDetectionDemo = () => {
  const [showDetection, setShowDetection] = useState(false);

  // Sample results data from your document
  const sampleResults = {
    id: 37,
    symbol_image_url: "/results/37/symbol-image",
    metadata: {
      summary: {
        component_count: 13,
        connection_count: 8,
        review_required_count: 13,
        warning_count: 0,
      },
      quality_metrics: {
        avg_detection_confidence: 0.958,
        tagged_components_ratio: 0.0,
        connected_components_ratio: 0.846,
      },
      timings_ms: {
        total: 7529,
      },
    },
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-4">
            AI Detection Viewer
          </h1>
          <p className="text-slate-400 mb-8">
            Click the button below to view the AI detection results
            visualization
          </p>

          <button
            onClick={() => setShowDetection(true)}
            className="bg-gradient-to-r from-blue-500 to-cyan-400 text-white px-6 py-3 rounded-lg font-medium hover:shadow-lg transition-all flex items-center space-x-2 mx-auto"
          >
            <Eye className="w-5 h-5" />
            <span>View AI Detection Results</span>
          </button>
        </div>

        {/* Sample stats preview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
            <div className="text-2xl font-bold text-cyan-400">13</div>
            <div className="text-slate-300 text-sm">Components</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
            <div className="text-2xl font-bold text-green-400">8</div>
            <div className="text-slate-300 text-sm">Connections</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
            <div className="text-2xl font-bold text-purple-400">95.8%</div>
            <div className="text-slate-300 text-sm">Avg Confidence</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
            <div className="text-2xl font-bold text-orange-400">7.5s</div>
            <div className="text-slate-300 text-sm">Processing Time</div>
          </div>
        </div>

        <AIDetectionViewer
          results={sampleResults}
          isOpen={showDetection}
          onClose={() => setShowDetection(false)}
        />
      </div>
    </div>
  );
};

export default AIDetectionDemo;
