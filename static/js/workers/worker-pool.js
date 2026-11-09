/**
 * StoryBrain AI — Client Web Worker Pool & Offload Harness
 * Manages background workers with automatic fallback, zero-copy buffer transfers,
 * and memory safety checks (50MB ceiling).
 */

(function () {
  'use strict';

  window.sbr = window.sbr || {};

  const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
  let imageWorkerInstance = null;
  let pdfWorkerInstance = null;
  let requestIdCounter = 0;
  const pendingRequests = new Map();

  function supportsWorkers() {
    return (
      typeof window !== 'undefined' &&
      typeof window.Worker !== 'undefined' &&
      typeof window.OffscreenCanvas !== 'undefined'
    );
  }

  function getImageWorker() {
    if (!imageWorkerInstance) {
      try {
        imageWorkerInstance = new Worker('/static/js/workers/image.worker.js');
        imageWorkerInstance.onmessage = function (e) {
          const { id, success, error, ...data } = e.data;
          const handler = pendingRequests.get(id);
          if (handler) {
            pendingRequests.delete(id);
            if (success) {
              handler.resolve(data);
            } else {
              handler.reject(new Error(error || 'Worker operation failed'));
            }
          }
        };
        imageWorkerInstance.onerror = function (err) {
          console.warn('[sbr-worker] Image worker error:', err);
        };
      } catch (e) {
        console.warn('[sbr-worker] Could not instantiate Image Worker:', e);
        return null;
      }
    }
    return imageWorkerInstance;
  }

  function getPdfWorker() {
    if (!pdfWorkerInstance) {
      try {
        pdfWorkerInstance = new Worker('/static/js/workers/pdf.worker.js');
        pdfWorkerInstance.onmessage = function (e) {
          const { id, success, error, ...data } = e.data;
          const handler = pendingRequests.get(id);
          if (handler) {
            pendingRequests.delete(id);
            if (success) {
              handler.resolve(data);
            } else {
              handler.reject(new Error(error || 'PDF worker operation failed'));
            }
          }
        };
      } catch (e) {
        console.warn('[sbr-worker] Could not instantiate PDF Worker:', e);
        return null;
      }
    }
    return pdfWorkerInstance;
  }

  /**
   * Main-thread fallback for image compression when Web Workers or OffscreenCanvas are disabled.
   */
  async function fallbackCompress(blob, options) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const url = URL.createObjectURL(blob);
      img.onload = () => {
        URL.revokeObjectURL(url);
        try {
          let targetWidth = img.width;
          let targetHeight = img.height;

          if (options.maxWidth && targetWidth > options.maxWidth) {
            const ratio = options.maxWidth / targetWidth;
            targetWidth = options.maxWidth;
            targetHeight = Math.round(targetHeight * ratio);
          }
          if (options.maxHeight && targetHeight > options.maxHeight) {
            const ratio = options.maxHeight / targetHeight;
            targetHeight = options.maxHeight;
            targetWidth = Math.round(targetWidth * ratio);
          }

          const canvas = document.createElement('canvas');
          canvas.width = targetWidth;
          canvas.height = targetHeight;
          const ctx = canvas.getContext('2d');
          if (!ctx) throw new Error('Cannot acquire canvas 2D context');

          ctx.drawImage(img, 0, 0, targetWidth, targetHeight);
          const mime = options.mimeType || 'image/jpeg';
          const quality = typeof options.quality === 'number' ? options.quality : 0.8;

          canvas.toBlob(
            (outBlob) => {
              if (!outBlob) {
                reject(new Error('Canvas export failed'));
                return;
              }
              resolve({
                blob: outBlob,
                mimeType: mime,
                width: targetWidth,
                height: targetHeight,
                originalSize: blob.size,
                compressedSize: outBlob.size,
              });
            },
            mime,
            quality
          );
        } catch (err) {
          reject(err);
        }
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error('Failed to load image in fallback pipeline'));
      };
      img.src = url;
    });
  }

  /**
   * Offload image compression/resizing with memory guard.
   */
  async function compressImage(fileOrBlob, options = {}) {
    if (!fileOrBlob) throw new Error('No file provided for compression');

    if (fileOrBlob.size > MAX_FILE_SIZE) {
      throw new Error(
        `File size (${(fileOrBlob.size / 1048576).toFixed(1)}MB) exceeds maximum safe client limit of 50MB.`
      );
    }

    const worker = supportsWorkers() ? getImageWorker() : null;

    if (!worker) {
      return fallbackCompress(fileOrBlob, options);
    }

    const buffer = await fileOrBlob.arrayBuffer();
    const reqId = ++requestIdCounter;

    return new Promise((resolve, reject) => {
      pendingRequests.set(reqId, {
        resolve: (data) => {
          const resBlob = new Blob([data.buffer], { type: data.mimeType });
          resolve({
            blob: resBlob,
            ...data,
          });
        },
        reject,
      });

      // Transfer ArrayBuffer with zero-copy transfer
      worker.postMessage(
        {
          id: reqId,
          action: 'compress',
          buffer,
          mimeType: options.mimeType || fileOrBlob.type || 'image/jpeg',
          quality: typeof options.quality === 'number' ? options.quality : 0.8,
          maxWidth: options.maxWidth,
          maxHeight: options.maxHeight,
        },
        [buffer]
      );
    });
  }

  /**
   * Analyze PDF structure off-thread.
   */
  async function analyzePdf(fileOrBlob) {
    if (!fileOrBlob) throw new Error('No PDF file provided');
    if (fileOrBlob.size > MAX_FILE_SIZE) {
      throw new Error(`PDF exceeds 50MB safety limit (${(fileOrBlob.size / 1048576).toFixed(1)}MB).`);
    }

    const worker = getPdfWorker();
    if (!worker) {
      return { isPdf: true, estimatedPages: 1, sizeBytes: fileOrBlob.size };
    }

    const buffer = await fileOrBlob.arrayBuffer();
    const reqId = ++requestIdCounter;

    return new Promise((resolve, reject) => {
      pendingRequests.set(reqId, { resolve, reject });
      worker.postMessage(
        {
          id: reqId,
          action: 'analyze_structure',
          buffer,
        },
        [buffer]
      );
    });
  }

  // Public API
  window.sbr.workers = {
    supportsWorkers,
    compressImage,
    analyzePdf,
    terminateAll: function () {
      if (imageWorkerInstance) {
        imageWorkerInstance.terminate();
        imageWorkerInstance = null;
      }
      if (pdfWorkerInstance) {
        pdfWorkerInstance.terminate();
        pdfWorkerInstance = null;
      }
    },
  };
})();
