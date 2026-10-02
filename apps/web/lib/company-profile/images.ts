"use client";

// Browser-side checks for the logo and banner before they upload (WS-001). The API checks
// again; these only spare the Admin a round trip. SVG logos are drawn to a PNG here, so the
// server never parses SVG and emails (which can't show SVG) get a PNG.

import {
  BANNER_TYPES,
  IMAGE_MAX_BYTES,
  LOGO_RASTER_SIDE,
  LOGO_TYPES,
  logoSizeError,
} from "@/lib/company-profile";
import type { MessageKey } from "@/lib/i18n";

export type Prepared = { file: File } | { error: MessageKey };

function loadImage(file: File): Promise<HTMLImageElement> {
  const url = URL.createObjectURL(file);
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("image did not load"));
    };
    image.src = url;
  });
}

function canvasPng(canvas: HTMLCanvasElement): Promise<Blob | null> {
  return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
}

async function rasteriseSvg(file: File): Promise<Prepared> {
  let image: HTMLImageElement;
  try {
    image = await loadImage(file);
  } catch {
    return { error: "companyProfile.errors.svgUnreadable" };
  }
  const { naturalWidth: width, naturalHeight: height } = image;
  if (!width || !height || Math.abs(width - height) / Math.max(width, height) > 0.01) {
    return { error: "companyProfile.errors.logoNotSquare" };
  }
  const canvas = document.createElement("canvas");
  canvas.width = LOGO_RASTER_SIDE;
  canvas.height = LOGO_RASTER_SIDE;
  try {
    canvas.getContext("2d")?.drawImage(image, 0, 0, LOGO_RASTER_SIDE, LOGO_RASTER_SIDE);
    const blob = await canvasPng(canvas);
    if (!blob) return { error: "companyProfile.errors.svgUnreadable" };
    const name = file.name.replace(/\.svg$/i, "") + ".png";
    return { file: new File([blob], name, { type: "image/png" }) };
  } catch {
    // Some browsers refuse to export a canvas an SVG was drawn on.
    return { error: "companyProfile.errors.svgUnreadable" };
  }
}

export async function prepareLogo(file: File): Promise<Prepared> {
  if (!LOGO_TYPES.includes(file.type)) return { error: "companyProfile.errors.logoType" };
  if (file.size > IMAGE_MAX_BYTES) return { error: "companyProfile.errors.imageTooLarge" };
  if (file.type === "image/svg+xml") return rasteriseSvg(file);
  try {
    const image = await loadImage(file);
    const error = logoSizeError(image.naturalWidth, image.naturalHeight);
    return error ? { error } : { file };
  } catch {
    return { error: "companyProfile.errors.imageInvalid" };
  }
}

export async function prepareBanner(file: File): Promise<Prepared> {
  if (!BANNER_TYPES.includes(file.type)) return { error: "companyProfile.errors.bannerType" };
  if (file.size > IMAGE_MAX_BYTES) return { error: "companyProfile.errors.imageTooLarge" };
  try {
    await loadImage(file);
    return { file };
  } catch {
    return { error: "companyProfile.errors.imageInvalid" };
  }
}
