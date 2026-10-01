"""
image_processing/preprocess.py
---------------------------------
Module 3: Answer Sheet Scanning Module
Image preprocessing pipeline for scanned/photographed answer sheets.

Steps applied (in order):
  1. Resize (cap max dimension for consistent, fast processing)
  2. Grayscale conversion
  3. Contrast enhancement (CLAHE)
  4. Noise removal (denoising)
  5. Deskew (straighten rotated pages)
  6. Adaptive thresholding (binarize for cleaner OCR)
  7. Sharpening
"""

import cv2
import numpy as np


MAX_DIMENSION = 2000


def _resize(image):
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest > MAX_DIMENSION:
        scale = MAX_DIMENSION / longest
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return image


def _grayscale(image):
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def _enhance_contrast(gray):
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _remove_noise(gray):
    return cv2.fastNlMeansDenoising(gray, h=10)


def _deskew(gray):
    """Detects the dominant skew angle of the text block and rotates to correct it."""
    inverted = cv2.bitwise_not(gray)
    thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))

    if coords.shape[0] < 50:
        return gray  # not enough foreground pixels to reliably detect skew

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Ignore negligible or clearly-wrong angles rather than over-rotating.
    if abs(angle) < 0.3 or abs(angle) > 15:
        return gray

    (h, w) = gray.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def _threshold(gray):
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )


def _sharpen(image):
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    return cv2.filter2D(image, -1, kernel)


def preprocess_image(input_path, output_path):
    """
    Runs the full preprocessing pipeline on the image at input_path
    and writes the result to output_path.
    Returns output_path on success.
    """
    image = cv2.imread(input_path)
    if image is None:
        raise ValueError(f"Could not read image at {input_path}")

    image = _resize(image)
    gray = _grayscale(image)
    gray = _enhance_contrast(gray)
    gray = _remove_noise(gray)
    gray = _deskew(gray)
    binary = _threshold(gray)
    result = _sharpen(binary)

    cv2.imwrite(output_path, result)
    return output_path
