const DOWNLOAD_STORAGE_KEY = "downloadSettings";

export const DOWNLOAD_DEFAULTS = {
  useFilePicker: true,
  formatName: "formatted.html",
  zipName: "extracted.zip",
  tsxName: "project.zip",
  ejsName: "project-ejs.zip",
};

const PICKER_TYPES: Record<
  string,
  { description: string; accept: Record<string, string[]> }[]
> = {
  html: [{ description: "HTML File", accept: { "text/html": [".html"] } }],
  zip: [
    { description: "ZIP Archive", accept: { "application/zip": [".zip"] } },
  ],
  pdf: [
    { description: "PDF Document", accept: { "application/pdf": [".pdf"] } },
  ],
  csv: [{ description: "CSV File", accept: { "text/csv": [".csv"] } }],
  json: [
    { description: "JSON File", accept: { "application/json": [".json"] } },
  ],
};

export function supportsFilePicker(): boolean {
  return typeof window !== "undefined" && "showSaveFilePicker" in window;
}

function sanitizeFilename(name: string, fallback: string): string {
  const trimmed = (name || "").trim();
  if (!trimmed) return fallback;
  return trimmed.replace(/[\\\/<>:"|?*]+/g, "-");
}

function ensureExtension(name: string, extension: string): string {
  if (!extension) return name;
  if (name.toLowerCase().endsWith(extension.toLowerCase())) return name;
  return `${name}${extension}`;
}

export function resolveDownloadName(
  inputId: string,
  fallbackName: string,
  extension: string
): string {
  const input = document.getElementById(inputId) as HTMLInputElement | null;
  const rawName = input ? input.value : "";
  const sanitized = sanitizeFilename(rawName, fallbackName);
  return ensureExtension(sanitized, extension);
}

export interface DownloadSettings {
  useFilePicker: boolean;
  formatName: string;
  zipName: string;
  tsxName: string;
  ejsName: string;
}

export function loadDownloadSettings(): DownloadSettings {
  try {
    const stored = JSON.parse(
      localStorage.getItem(DOWNLOAD_STORAGE_KEY) || "{}"
    );
    return { ...DOWNLOAD_DEFAULTS, ...stored };
  } catch {
    return { ...DOWNLOAD_DEFAULTS };
  }
}

export function storeDownloadSettings(settings: Partial<DownloadSettings>) {
  try {
    const current = loadDownloadSettings();
    localStorage.setItem(
      DOWNLOAD_STORAGE_KEY,
      JSON.stringify({ ...current, ...settings })
    );
  } catch (error) {
    console.warn("Failed to store download settings.", error);
  }
}

function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function saveBlobWithPicker(
  blob: Blob,
  filename: string,
  pickerTypes: { description: string; accept: Record<string, string[]> }[]
): Promise<"saved" | "canceled" | "fallback"> {
  if (!supportsFilePicker()) return "fallback";

  try {
    const handle = await (window as any).showSaveFilePicker({
      suggestedName: filename,
      types: pickerTypes,
      excludeAcceptAllOption: false,
    });
    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return "saved";
  } catch (error: any) {
    if (error && error.name === "AbortError") return "canceled";
    return "fallback";
  }
}

export async function downloadBlob(
  blob: Blob,
  filename: string,
  type: "html" | "zip" | "pdf" | "csv" | "json",
  useFilePicker: boolean
): Promise<"saved" | "canceled" | "downloaded"> {
  if (useFilePicker && supportsFilePicker()) {
    const result = await saveBlobWithPicker(blob, filename, PICKER_TYPES[type]);
    if (result !== "fallback") return result === "saved" ? "saved" : "canceled";
  }
  triggerBrowserDownload(blob, filename);
  return "downloaded";
}
