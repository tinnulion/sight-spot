This project contains fully-functional visual attention detector module. It`s implemented on pure Python. Framework uses only Pillow, NumPy and SciPy modules.

Key functions are the following:

Saliency map generation.
Heatmap generation, another view of saliency map.
Improve saliency map by SLIC segmetation of input image (gives pixel-precision segmentation).
Thresholding (automatic threshold calculation available).
Foreground extraction (background pixel with be black).
Bounding boxes detection.
