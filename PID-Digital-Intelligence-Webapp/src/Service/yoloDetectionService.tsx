import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "multipart/form-data",
  },
});

const jsonApiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Get detection output from YOLO model
 * @param {File} file - The image, PDF, or DXF file to analyze
 * @returns {Promise<Object|null>} Detection results or null on error
 */
export const getPrediction = async (file) => {
  try {
    if (!file) throw new Error("File is required");

    // Allowed MIME types
    const validMimeTypes = [
      "image/jpeg",
      "image/png",
      "image/jpg",
      "application/pdf",
      "application/dxf",
      "image/vnd.dxf",
      "application/octet-stream", // DXF fallback
    ];

    // Allowed extensions
    const validExtensions = [".jpeg", ".jpg", ".png", ".pdf", ".dxf"];

    const fileExt = file.name
      .substring(file.name.lastIndexOf("."))
      .toLowerCase();

    if (
      !validMimeTypes.includes(file.type) &&
      !validExtensions.includes(fileExt)
    ) {
      throw new Error("Only JPEG, PNG, PDF, or DXF files are allowed");
    }

    const formData = new FormData();
    formData.append("file", file);

    const response = await apiClient.post("/process", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  } catch (error) {
    console.error("Detection API Error:", error.message);
    return null;
  }
};

/**
 * Export results to DXF format
 * @param {Object} analysisData - The analysis results data
 * @returns {Promise<Blob|null>} DXF file blob or null on error
 */
export const exportToDXF = async (analysisData) => {
  try {
    if (!analysisData) throw new Error("Analysis data is required");

    const response = await jsonApiClient.post("/export/dxf", analysisData, {
      responseType: "blob", // Important for file downloads
    });

    return response.data;
  } catch (error) {
    console.error("DXF Export API Error:", error.message);
    throw error;
  }
};

/**
 * Fetch the AI detection visualization image
 * @param {string} symbolImageUrl - The symbol image URL from the analysis results
 * @returns {Promise<Blob|null>} Image blob or null on error
 */
export const getDetectionImage = async (symbolImageUrl) => {
  try {
    if (!symbolImageUrl) throw new Error("Symbol image URL is required");

    // Use the jsonApiClient but override response type for blob
    const response = await jsonApiClient.get(symbolImageUrl, {
      responseType: "blob",
      headers: {
        "Content-Type": "application/json", // This will be overridden by responseType
      },
    });

    return response.data;
  } catch (error) {
    console.error("Detection Image API Error:", error.message);
    throw error;
  }
};
