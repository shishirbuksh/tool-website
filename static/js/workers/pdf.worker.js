/**
 * StoryBrain AI — PDF Processing Web Worker
 * Offloads compute-heavy PDF parsing, text extraction, and page chunking off main thread.
 * Strict client-side RAM sandbox: zero network transmission.
 */

'use strict';

const MAX_PAYLOAD_BYTES = 50 * 1024 * 1024; // 50MB ceiling safeguard

self.onmessage = async function (e) {
  const { id, action, buffer, options } = e.data;

  try {
    if (!buffer || buffer.byteLength === 0) {
      throw new Error('Empty PDF buffer received');
    }

    if (buffer.byteLength > MAX_PAYLOAD_BYTES) {
      throw new Error(
        `PDF payload exceeds 50MB safety ceiling (${(buffer.byteLength / 1048576).toFixed(1)}MB). Aborted to prevent memory crash.`
      );
    }

    if (action === 'analyze_structure') {
      const bytes = new Uint8Array(buffer);
      const str = String.fromCharCode.apply(null, bytes.subarray(0, Math.min(bytes.length, 2048)));
      
      // Basic header verification (%PDF-1.x)
      const isPdf = str.startsWith('%PDF-');
      const versionMatch = str.match(/%PDF-(\d+\.\d+)/);
      const version = versionMatch ? versionMatch[1] : 'Unknown';

      // Scan for rough page object count
      let pageCount = 0;
      const textDecoder = new TextDecoder('latin1');
      const fullText = textDecoder.decode(bytes);
      const matches = fullText.match(/\/Type\s*\/Page[^s]/g);
      pageCount = matches ? matches.length : 1;

      self.postMessage({
        id,
        success: true,
        isPdf,
        version,
        estimatedPages: pageCount,
        sizeBytes: buffer.byteLength,
      });
    } else {
      throw new Error(`Unknown PDF worker action: ${action}`);
    }
  } catch (err) {
    self.postMessage({
      id,
      success: false,
      error: err.message || 'PDF worker execution error',
    });
  }
};
