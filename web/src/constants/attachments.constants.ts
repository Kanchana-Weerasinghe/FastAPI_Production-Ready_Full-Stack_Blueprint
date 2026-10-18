import docIcon from "../assets/images/doc.webp";
import jsonIcon from "../assets/images/json.webp";
import pdfIcon from "../assets/images/pdf.webp";
import pptIcon from "../assets/images/ppt.webp";
import xlsIcon from "../assets/images/xls.webp";

/**
 * List of file extensions permitted for upload.
 */
export const ALLOWED_EXTENSIONS = [
  ".pdf",
  ".xls",
  ".xlsx",
  ".docx",
  ".pptx",
  ".doc",
  ".ppt",
  ".json",
];

/**
 * Resolves the appropriate visual icon for a file based on its extension.
 *
 * @param fileName - The full name of the file including extension.
 * @returns The imported image asset for the file type.
 */
export const getAttachmentIcon = (fileName: string) => {
  const ext = fileName.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "pdf":
      return pdfIcon;
    case "doc":
    case "docx":
      return docIcon;
    case "xls":
    case "xlsx":
      return xlsIcon;
    case "ppt":
    case "pptx":
      return pptIcon;
    case "json":
      return jsonIcon;
    default:
      return pdfIcon;
  }
};
