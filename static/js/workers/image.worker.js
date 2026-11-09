/**
 * StoryBrain AI — High-Performance Image Web Worker
 * Offloads canvas resizing, format conversion, and compression off the main thread.
 * Strict client-side RAM sandbox: zero network transmission.
 */

'use strict';

const MAX_PAYLOAD_BYTES = 50 * 1024 * 1024; // 50MB ceiling safeguard

self.onmessage = async function (e) {
  const { id, action, buffer, mimeType, quality, maxWidth, maxHeight } = e.data;

  try {
    if (!buffer || buffer.byteLength === 0) {
      throw new Error('Empty image buffer received');
    }

    if (buffer.byteLength > MAX_PAYLOAD_BYTES) {
      throw new Error(
        `Payload exceeds 50MB boundary safety ceiling (${(buffer.byteLength / 1048576).toFixed(1)}MB). Aborted to prevent browser OOM.`
      );
    }

    if (action === 'compress' || action === 'resize') {
      const blob = new Blob([buffer], { type: mimeType || 'image/jpeg' });
      const imageBitmap = await createImageBitmap(blob);

      let targetWidth = imageBitmap.width;
      let targetHeight = imageBitmap.height;

      // Handle aspect-ratio resizing if constrained
      if (maxWidth && targetWidth > maxWidth) {
        const ratio = maxWidth / targetWidth;
        targetWidth = maxWidth;
        targetHeight = Math.round(targetHeight * ratio);
      }
      if (maxHeight && targetHeight > maxHeight) {
        const ratio = maxHeight / targetHeight;
        targetHeight = maxHeight;
        targetWidth = Math.round(targetWidth * ratio);
      }

      // Check for OffscreenCanvas support
      if (typeof OffscreenCanvas !== 'undefined') {
        const offscreen = new OffscreenCanvas(targetWidth, targetHeight);
        const ctx = offscreen.getContext('2d');
        if (!ctx) throw new Error('Failed to acquire OffscreenCanvas 2D context');

        ctx.drawImage(imageBitmap, 0, 0, targetWidth, targetHeight);

        const targetMime = mimeType || 'image/jpeg';
        const targetQuality = typeof quality === 'number' ? quality : 0.8;

        const resultBlob = await offscreen.convertToBlob({
          type: targetMime,
          quality: targetQuality,
        });

        const outputBuffer = await resultBlob.arrayBuffer();

        // Transfer output buffer back with zero-copy
        self.postMessage(
          {
            id,
            success: true,
            buffer: outputBuffer,
            mimeType: targetMime,
            width: targetWidth,
            height: targetHeight,
            originalSize: buffer.byteLength,
            compressedSize: outputBuffer.byteLength,
          },
          [outputBuffer]
        );
      } else {
        throw new Error('OffscreenCanvas unsupported in this worker context');
      }
    } else {
      throw new Error(`Unknown worker action: ${action}`);
    }
  } catch (err) {
    self.postMessage({
      id,
      success: false,
      error: err.message || 'Worker computation error',
    });
  }
};
