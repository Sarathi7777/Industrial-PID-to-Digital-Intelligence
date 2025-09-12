import React, { useState, useRef } from "react";
import {
  Upload,
  FileText,
  Download,
  CheckCircle,
  Eye,
  Settings,
  Play,
  AlertTriangle,
  Info,
  Loader2,
  AlertCircle,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Search,
  X,
  MessageCircle,
  Brain,
  Cpu,
  Zap,
} from "lucide-react";

import { toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import {
  exportToDXF,
  getPrediction,
  getDetectionImage,
} from "../Service/yoloDetectionService";
import { useChat } from "../contexts/ChatContext";

// Inline AI Detection Component
const InlineAIDetectionViewer = ({ results }) => {
  const [imageUrl, setImageUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageLoaded, setImageLoaded] = useState(false);

  const fetchDetectionImage = async () => {
    if (!results?.symbol_image_url || imageLoaded) return;

    setLoading(true);
    setError(null);

    try {
      const blob = await getDetectionImage(results.symbol_image_url);
      const url = URL.createObjectURL(blob);
      setImageUrl(url);
      setImageLoaded(true);
    } catch (err) {
      console.error("Error fetching detection image:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Auto-load when component mounts
  React.useEffect(() => {
    if (results?.symbol_image_url && !imageLoaded) {
      fetchDetectionImage();
    }

    // Cleanup on unmount
    return () => {
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [results]);

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

  if (!results) return null;

  return (
    <div className="bg-slate-800/30 rounded-xl border border-slate-700 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-slate-700">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full flex items-center justify-center">
            <Eye className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-white">
              AI Detection Results
            </h3>
            <p className="text-slate-400 text-sm">
              Detected symbols and components visualization
            </p>
          </div>
        </div>

        {/* Controls */}
        {imageUrl && (
          <div className="flex items-center space-x-2">
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
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-6">
        {loading && (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <Loader2 className="w-12 h-12 text-cyan-400 animate-spin mx-auto mb-4" />
              <p className="text-slate-300">Loading AI detection results...</p>
              <p className="text-slate-500 text-sm mt-1">
                Fetching annotated image from server
              </p>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-64">
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
              className="relative overflow-hidden h-[500px] cursor-move"
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
          <div className="flex items-center justify-center h-64">
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
  );
};

const PIDUploadComponent = () => {
  const [file, setFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [activeTab, setActiveTab] = useState("upload");
  const [exportingDXF, setExportingDXF] = useState(false);
  const [currentProcessingMessage, setCurrentProcessingMessage] = useState("");
  const fileInputRef = useRef(null);

  // Use global chat context
  const { setPidData, openChat } = useChat();

  // Filter state variables
  const [filterText, setFilterText] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [confidenceFilter, setConfidenceFilter] = useState("all");
  const [classFilter, setClassFilter] = useState("all");

  const processingMessages = [
    {
      message: "Uploading diagram to AI servers...",
      icon: Upload,
      duration: 2000,
    },
    {
      message: "Preprocessing image for optimal analysis...",
      icon: Settings,
      duration: 3000,
    },
    {
      message: "AI is detecting symbols and components...",
      icon: Brain,
      duration: 4000,
    },
    {
      message: "Extracting text labels and annotations...",
      icon: FileText,
      duration: 3000,
    },
    {
      message: "Mapping process flow connections...",
      icon: Zap,
      duration: 3500,
    },
    {
      message: "Validating detected components...",
      icon: CheckCircle,
      duration: 2500,
    },
    {
      message: "Generating final analysis report...",
      icon: Cpu,
      duration: 2000,
    },
  ];

  const handleFileUpload = (event) => {
    const uploadedFile = event.target.files?.[0];
    if (uploadedFile) {
      setFile(uploadedFile);
      setActiveTab("preview");
    }
  };

  const startProcessing = async () => {
    if (!file) return;

    setProcessing(true);
    setActiveTab("processing");

    try {
      // Show processing messages while API call is happening
      let messageIndex = 0;

      // Start the API call immediately
      const apiPromise = getPrediction(file);

      // Show processing messages
      const showNextMessage = () => {
        if (messageIndex < processingMessages.length && processing) {
          const currentMsg = processingMessages[messageIndex];
          setCurrentProcessingMessage(currentMsg.message);
          messageIndex++;

          setTimeout(showNextMessage, currentMsg.duration);
        }
      };

      // Start showing messages
      showNextMessage();

      // Wait for API response
      const response = await apiPromise;
      console.log("API Response:", response);

      // Set the actual API response
      setResults(response);
      // Update global chat context with P&ID data
      setPidData(response);

      // Show completion message briefly
      setCurrentProcessingMessage("Analysis complete! Preparing results...");
      await new Promise((resolve) => setTimeout(resolve, 1500));

      // Navigate to results tab if we have a successful response
      if (response) {
        setActiveTab("results");
      }
    } catch (error) {
      console.error("Error during processing:", error);
      setCurrentProcessingMessage("Analysis failed. Please try again.");
      toast.error("Failed to process P&ID. Please try again.");
      await new Promise((resolve) => setTimeout(resolve, 2000));
      // Stay on processing tab or go back to preview on error
      setActiveTab("preview");
    } finally {
      setProcessing(false);
    }
  };

  const downloadResults = (format) => {
    if (!results) return;

    const data =
      format === "json"
        ? JSON.stringify(results, null, 2)
        : format === "xml"
        ? convertToXML(results)
        : convertToCSV(results);

    const blob = new Blob([data], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `pid-analysis.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const convertToXML = (data) => {
    return `<?xml version="1.0" encoding="UTF-8"?>
<PIDAnalysis>
  <Metadata>
    <DocumentName>${data.metadata.document_name}</DocumentName>
    <ProcessingTimestamp>${new Date().toISOString()}</ProcessingTimestamp>
    <Summary>
      <ComponentCount>${data.metadata.summary.component_count}</ComponentCount>
      <ConnectionCount>${
        data.metadata.summary.connection_count
      }</ConnectionCount>
      <ReviewRequiredCount>${
        data.metadata.summary.review_required_count
      }</ReviewRequiredCount>
      <WarningCount>${data.metadata.summary.warning_count}</WarningCount>
    </Summary>
    <QualityMetrics>
      <AvgDetectionConfidence>${
        data.metadata.quality_metrics.avg_detection_confidence
      }</AvgDetectionConfidence>
      <TaggedComponentsRatio>${
        data.metadata.quality_metrics.tagged_components_ratio
      }</TaggedComponentsRatio>
      <ConnectedComponentsRatio>${
        data.metadata.quality_metrics.connected_components_ratio
      }</ConnectedComponentsRatio>
    </QualityMetrics>
  </Metadata>
  <Components>
    ${data.components
      .map(
        (comp) => `
    <Component id="${comp.component_id}" class="${
          comp.component_class_name
        }" status="${comp.status}">
      <PIDTag>${comp.pid_tag || "N/A"}</PIDTag>
      <BoundingBox>${comp.attributes.bbox_pixels.join(",")}</BoundingBox>
      <Confidence>${comp.attributes.detection_confidence}</Confidence>
      <ConnectionsTo>${comp.connections_to.join(",")}</ConnectionsTo>
    </Component>`
      )
      .join("")}
  </Components>
  <Connections>
    ${data.connections_summary
      .map(
        (conn) => `
    <Connection from="${conn.from}" to="${conn.to}" status="${conn.status}"/>`
      )
      .join("")}
  </Connections>
</PIDAnalysis>`;
  };

  const convertToCSV = (data) => {
    const components = data.components
      .map(
        (c) =>
          `${c.component_id},${c.component_class_name},${c.pid_tag || "N/A"},${
            c.status
          },${
            c.attributes.detection_confidence
          },${c.attributes.bbox_pixels.join(";")}`
      )
      .join("\n");
    return `Component ID,Class,PID Tag,Status,Confidence,Bounding Box\n${components}`;
  };

  const downloadDXF = async () => {
    if (!results) return;

    setExportingDXF(true);
    try {
      const dxfBlob = await exportToDXF(results);

      // Create download link
      const url = URL.createObjectURL(dxfBlob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pid-analysis.dxf`;
      document.body.appendChild(a);
      a.click();

      // Clean up
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast.success("DXF file downloaded successfully!");
    } catch (error) {
      console.error("Failed to download DXF:", error);
      toast.error("Failed to export DXF file. Please try again.");
    } finally {
      setExportingDXF(false);
    }
  };

  // Calculate stats for display
  const calculateStats = () => {
    if (!results) return null;

    return {
      totalComponents: results.metadata.summary.component_count,
      totalConnections: results.metadata.summary.connection_count,
      reviewRequired: results.metadata.summary.review_required_count,
      warningCount: results.metadata.summary.warning_count,
      avgConfidence: results.metadata.quality_metrics.avg_detection_confidence,
      taggedRatio: results.metadata.quality_metrics.tagged_components_ratio,
      connectedRatio:
        results.metadata.quality_metrics.connected_components_ratio,
    };
  };

  const getStatusIcon = (status) => {
    if (status === "OK") {
      return <CheckCircle className="w-4 h-4 text-green-400" />;
    } else if (status.startsWith("Warning")) {
      return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
    } else if (status.startsWith("Review Required")) {
      return <Info className="w-4 h-4 text-red-400" />;
    }
    return <Info className="w-4 h-4 text-gray-400" />;
  };

  const getStatusColor = (status) => {
    if (status === "OK") return "text-green-400";
    if (status.startsWith("Warning")) return "text-yellow-400";
    if (status.startsWith("Review Required")) return "text-red-400";
    return "text-gray-400";
  };

  // Filter components based on filter criteria
  const filteredComponents = results?.components
    ? results.components.filter((comp) => {
        // Filter by text search (ID, PID Tag, or Class)
        const matchesText =
          comp.component_id.toLowerCase().includes(filterText.toLowerCase()) ||
          (comp.pid_tag &&
            comp.pid_tag.toLowerCase().includes(filterText.toLowerCase())) ||
          comp.component_class_name
            .toLowerCase()
            .includes(filterText.toLowerCase());

        // Filter by status
        const matchesStatus =
          statusFilter === "all" || comp.status === statusFilter;

        // Filter by confidence
        let matchesConfidence = true;
        if (confidenceFilter === "high") {
          matchesConfidence = comp.attributes.detection_confidence >= 0.8;
        } else if (confidenceFilter === "medium") {
          matchesConfidence =
            comp.attributes.detection_confidence >= 0.5 &&
            comp.attributes.detection_confidence < 0.8;
        } else if (confidenceFilter === "low") {
          matchesConfidence = comp.attributes.detection_confidence < 0.5;
        }

        // Filter by class
        const matchesClass =
          classFilter === "all" || comp.component_class_name === classFilter;

        return (
          matchesText && matchesStatus && matchesConfidence && matchesClass
        );
      })
    : [];

  // Get unique values for filter dropdowns
  const statusOptions = results
    ? [...new Set(results.components.map((comp) => comp.status))]
    : [];

  const classOptions = results
    ? [...new Set(results.components.map((comp) => comp.component_class_name))]
    : [];

  const stats = calculateStats();

  return (
    <div className="w-full max-w-6xl mx-auto">
      {/* Navigation Tabs */}
      <div className="flex space-x-1 bg-slate-800/30 rounded-lg p-1 mb-8">
        {[
          { id: "upload", name: "Upload", icon: Upload },
          { id: "preview", name: "Preview", icon: Eye },
          { id: "processing", name: "Processing", icon: Settings },
          { id: "results", name: "Results", icon: CheckCircle },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            disabled={
              (tab.id === "preview" && !file) ||
              (tab.id === "processing" && !file) ||
              (tab.id === "results" && !results)
            }
            className={`flex items-center space-x-2 px-6 py-3 rounded-md font-medium transition-all ${
              activeTab === tab.id
                ? "bg-gradient-to-r from-blue-500 to-cyan-400 text-white shadow-lg"
                : "text-slate-400 hover:text-white hover:bg-slate-700/50 disabled:opacity-50 disabled:cursor-not-allowed"
            }`}
          >
            <tab.icon className="w-4 h-4" />
            <span>{tab.name}</span>
          </button>
        ))}
      </div>

      {/* Upload Tab */}
      {activeTab === "upload" && (
        <div className="bg-slate-800/30 rounded-xl p-8 border border-slate-700">
          <div className="text-center">
            <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full flex items-center justify-center mx-auto mb-6">
              <FileText className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-4">
              Upload Your P&ID
            </h2>
            <p className="text-slate-400 mb-8 max-w-2xl mx-auto">
              Upload your Process & Instrumentation Diagram in PDF, PNG, JPEG,
              or DXF. Our AI will analyze the diagram and extract all
              components, connections, and metadata.
            </p>

            <div
              className="border-2 border-dashed border-slate-600 rounded-lg p-12 mb-6 hover:border-cyan-400 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="w-12 h-12 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-300 text-lg mb-2">
                Click to upload or drag and drop
              </p>
              <p className="text-slate-500">PDF, PNG, JPEG, DXF up to 50MB</p>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.dxf"
              onChange={handleFileUpload}
              className="hidden"
            />

            {file && (
              <div className="bg-slate-700/50 rounded-lg p-4 mb-4">
                <div className="flex items-center justify-center space-x-3">
                  <FileText className="w-5 h-5 text-cyan-400" />
                  <span className="text-white font-medium">{file.name}</span>
                  <span className="text-slate-400">
                    ({(file.size / 1024 / 1024).toFixed(2)} MB)
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Preview Tab */}
      {activeTab === "preview" && file && (
        <div className="bg-slate-800/30 rounded-xl p-8 border border-slate-700">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-white">Document Preview</h2>
            <button
              onClick={startProcessing}
              className="bg-gradient-to-r from-blue-500 to-cyan-400 text-white px-6 py-3 rounded-lg font-medium hover:shadow-lg transition-all flex items-center space-x-2"
            >
              <Play className="w-4 h-4" />
              <span>Start Analysis</span>
            </button>
          </div>

          <div className="bg-slate-700/30 rounded-lg p-6">
            <div className="text-center mb-4">
              <p className="text-slate-300 mb-2">Preview: {file.name}</p>
              <p className="text-slate-500 text-sm">
                File size: {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>

            {/* Image Preview */}
            <div className="flex justify-center">
              <div className="max-w-4xl w-full">
                {file.type.startsWith("image/") ? (
                  <img
                    src={URL.createObjectURL(file)}
                    alt="P&ID Preview"
                    className="w-full h-auto max-h-96 object-contain rounded-lg border border-slate-600"
                    onLoad={(e) => {
                      URL.revokeObjectURL(e.target.src);
                    }}
                  />
                ) : file.type === "application/pdf" ? (
                  <div className="bg-slate-600/50 rounded-lg p-8 text-center">
                    <FileText className="w-16 h-16 text-slate-400 mx-auto mb-4" />
                    <p className="text-slate-300 text-lg">PDF Document</p>
                    <p className="text-slate-500">
                      PDF preview not available - ready for processing
                    </p>
                  </div>
                ) : (
                  <div className="bg-slate-600/50 rounded-lg p-8 text-center">
                    <FileText className="w-16 h-16 text-slate-400 mx-auto mb-4" />
                    <p className="text-slate-300 text-lg">Document uploaded</p>
                    <p className="text-slate-500">
                      Preview not available - ready for processing
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="text-center mt-4">
              <p className="text-green-400 text-sm flex items-center justify-center space-x-2">
                <CheckCircle className="w-4 h-4" />
                <span>Ready for processing</span>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Processing Tab */}
      {activeTab === "processing" && (
        <div className="bg-slate-800/30 rounded-xl p-8 border border-slate-700">
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full flex items-center justify-center mx-auto mb-6">
              <Brain className="w-10 h-10 text-white animate-pulse" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-4">
              AI Analysis in Progress
            </h2>
            <p className="text-slate-400 mb-6">
              Our advanced AI is analyzing your P&ID diagram...
            </p>
          </div>

          {/* Single Dynamic Loader */}
          <div className="max-w-2xl mx-auto">
            <div className="bg-slate-700/30 rounded-xl p-8 text-center">
              {/* Animated Icon */}
              <div className="mb-6">
                <div className="relative">
                  <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full flex items-center justify-center mx-auto">
                    <Loader2 className="w-8 h-8 text-white animate-spin" />
                  </div>
                  <div className="absolute inset-0 w-16 h-16 bg-gradient-to-r from-blue-500/20 to-cyan-400/20 rounded-full animate-ping mx-auto"></div>
                </div>
              </div>

              {/* Current Processing Message */}
              <div className="mb-6">
                <h3 className="text-xl font-semibold text-white mb-2">
                  {currentProcessingMessage || "Initializing analysis..."}
                </h3>
                <div className="w-full bg-slate-600/50 rounded-full h-2">
                  <div className="bg-gradient-to-r from-blue-500 to-cyan-400 h-2 rounded-full animate-pulse w-full"></div>
                </div>
              </div>

              {/* Processing Info */}
              <div className="text-slate-400 text-sm space-y-2">
                <p>Processing: {file?.name}</p>
              </div>

              {/* Animated Progress Indicators */}
              <div className="flex justify-center space-x-2 mt-6">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  ></div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Results Tab */}
      {activeTab === "results" && results && stats && (
        <div className="space-y-6">
          {/* Stats Overview */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-gradient-to-r from-blue-500 to-cyan-400 rounded-xl p-6 text-white">
              <div className="text-3xl font-bold">{stats.totalComponents}</div>
              <div className="text-blue-100">Total Components</div>
            </div>
            <div className="bg-gradient-to-r from-purple-500 to-violet-400 rounded-xl p-6 text-white">
              <div className="text-3xl font-bold">{stats.totalConnections}</div>
              <div className="text-purple-100">Connections</div>
            </div>
            <div className="bg-gradient-to-r from-orange-500 to-red-400 rounded-xl p-6 text-white">
              <div className="text-3xl font-bold">{stats.reviewRequired}</div>
              <div className="text-orange-100">Review Required</div>
            </div>
            <div className="bg-gradient-to-r from-yellow-500 to-amber-400 rounded-xl p-6 text-white">
              <div className="text-3xl font-bold">{stats.warningCount}</div>
              <div className="text-yellow-100">Warnings</div>
            </div>
          </div>

          {/* Quality Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700">
              <div className="text-2xl font-bold text-cyan-400">
                {(stats.avgConfidence * 100).toFixed(1)}%
              </div>
              <div className="text-slate-300">Avg Detection Confidence</div>
            </div>
            <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700">
              <div className="text-2xl font-bold text-green-400">
                {(stats.taggedRatio * 100).toFixed(1)}%
              </div>
              <div className="text-slate-300">Tagged Components</div>
            </div>
            <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700">
              <div className="text-2xl font-bold text-purple-400">
                {(stats.connectedRatio * 100).toFixed(1)}%
              </div>
              <div className="text-slate-300">Connected Components</div>
            </div>
          </div>

          {/* Metadata */}
          <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700">
            <h3 className="text-xl font-bold text-white mb-4">
              Analysis Metadata
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <span className="text-slate-400">Document Name:</span>
                <span className="text-white ml-2">
                  {results.metadata.document_name}
                </span>
              </div>
              <div>
                <span className="text-slate-400">Processing Time:</span>
                <span className="text-white ml-2">
                  {results.metadata.timings_ms.total}ms
                </span>
              </div>
              <div>
                <span className="text-slate-400">Status:</span>
                <span className="text-white ml-2">
                  {results.metadata.status}
                </span>
              </div>
              <div>
                <span className="text-slate-400">Device:</span>
                <span className="text-white ml-2">
                  {results.metadata.device}
                </span>
              </div>
            </div>
          </div>

          {/* Export Options */}
          <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700">
            <h3 className="text-xl font-bold text-white mb-4">
              Export Results
            </h3>
            <div className="flex flex-wrap gap-4">
              <button
                onClick={() => downloadResults("json")}
                className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
              >
                <Download className="w-4 h-4" />
                <span>JSON</span>
              </button>
              <button
                onClick={() => downloadResults("xml")}
                className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
              >
                <Download className="w-4 h-4" />
                <span>XML</span>
              </button>
              <button
                onClick={() => downloadResults("csv")}
                className="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
              >
                <Download className="w-4 h-4" />
                <span>CSV</span>
              </button>
              <button
                onClick={downloadDXF}
                disabled={exportingDXF}
                className="bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {exportingDXF ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                <span>{exportingDXF ? "Exporting..." : "DXF"}</span>
              </button>
              <button
                onClick={openChat}
                className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
              >
                <MessageCircle className="w-4 h-4" />
                <span>Ask AI Assistant</span>
              </button>
            </div>
          </div>

          {/* Inline AI Detection Viewer - Shows right before component tables */}
          <InlineAIDetectionViewer results={results} />

          {/* Components Table */}
          <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700">
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-4">
              <h3 className="text-xl font-bold text-white">
                Detected Components
              </h3>

              {/* Filter Controls */}
              <div className="flex flex-col sm:flex-row gap-2">
                {/* Text Filter */}
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search components..."
                    value={filterText}
                    onChange={(e) => setFilterText(e.target.value)}
                    className="bg-slate-700/50 border border-slate-600 text-white rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:ring-2 focus:ring-cyan-400 w-full sm:w-48"
                  />
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                  {filterText && (
                    <button
                      onClick={() => setFilterText("")}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-white"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {/* Class Filter */}
                <select
                  value={classFilter}
                  onChange={(e) => setClassFilter(e.target.value)}
                  className="bg-slate-700/50 border border-slate-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-cyan-400"
                >
                  <option value="all">All Classes</option>
                  {classOptions.map((className) => (
                    <option key={className} value={className}>
                      {className}
                    </option>
                  ))}
                </select>

                {/* Status Filter */}
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-slate-700/50 border border-slate-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-cyan-400"
                >
                  <option value="all">All Status</option>
                  {statusOptions.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>

                {/* Confidence Filter */}
                <select
                  value={confidenceFilter}
                  onChange={(e) => setConfidenceFilter(e.target.value)}
                  className="bg-slate-700/50 border border-slate-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-cyan-400"
                >
                  <option value="all">All Confidence</option>
                  <option value="high">High (≥80%)</option>
                  <option value="medium">Medium (50-79%)</option>
                  <option value="low">Low (&lt;50%)</option>
                </select>
              </div>
            </div>

            {/* Results Count */}
            <div className="mb-4 text-slate-400 text-sm">
              Showing {filteredComponents.length} of {results.components.length}{" "}
              components
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-600">
                    <th className="text-left py-3 text-slate-300">ID</th>
                    <th className="text-left py-3 text-slate-300">PID Tag</th>
                    <th className="text-left py-3 text-slate-300">Class</th>
                    <th className="text-left py-3 text-slate-300">Status</th>
                    <th className="text-left py-3 text-slate-300">
                      Confidence
                    </th>
                    <th className="text-left py-3 text-slate-300">
                      Connections
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredComponents.length > 0 ? (
                    filteredComponents.map((comp) => (
                      <tr
                        key={comp.component_id}
                        className="border-b border-slate-700/50 hover:bg-slate-700/20"
                      >
                        <td className="py-3 text-cyan-400 font-mono">
                          {comp.component_id}
                        </td>
                        <td className="py-3 text-white">
                          {comp.pid_tag || "N/A"}
                        </td>
                        <td className="py-3 text-slate-300">
                          {comp.component_class_name}
                        </td>
                        <td
                          className={`py-3 ${getStatusColor(
                            comp.status
                          )} flex items-center space-x-2`}
                        >
                          {getStatusIcon(comp.status)}
                          <span>{comp.status}</span>
                        </td>
                        <td className="py-3 text-slate-400">
                          {(comp.attributes.detection_confidence * 100).toFixed(
                            1
                          )}
                          %
                        </td>
                        <td className="py-3 text-slate-400">
                          {comp.connections_to.length > 0
                            ? comp.connections_to.join(", ")
                            : "None"}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td
                        colSpan="6"
                        className="py-8 text-center text-slate-400"
                      >
                        No components match your filters
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Connections Table */}
          <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700">
            <h3 className="text-xl font-bold text-white mb-4">
              Connection Summary
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-600">
                    <th className="text-left py-3 text-slate-300">From</th>
                    <th className="text-left py-3 text-slate-300">To</th>
                    <th className="text-left py-3 text-slate-300">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {results.connections_summary.map((conn, index) => (
                    <tr
                      key={index}
                      className="border-b border-slate-700/50 hover:bg-slate-700/20"
                    >
                      <td className="py-3 text-cyan-400 font-mono">
                        {conn.from}
                      </td>
                      <td className="py-3 text-cyan-400 font-mono">
                        {conn.to}
                      </td>
                      <td className={`py-3 ${getStatusColor(conn.status)}`}>
                        {conn.status}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PIDUploadComponent;
