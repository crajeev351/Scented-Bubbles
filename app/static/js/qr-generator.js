/**
 * Scented Bubbles - Lightweight Native SVG QR Code Generator
 * Pure JavaScript, zero dependencies, offline-first, instant 60fps render.
 * Generates standards-compliant QR Codes (ISO/IEC 18004) for UPI payments.
 */
(function(window) {
  'use strict';

  // Standard QR Code constants & Galois Field tables for Reed-Solomon error correction
  const GF256_EXP = new Uint8Array(512);
  const GF256_LOG = new Uint8Array(256);
  (function initGF() {
    let x = 1;
    for (let i = 0; i < 255; i++) {
      GF256_EXP[i] = x;
      GF256_EXP[i + 255] = x;
      GF256_LOG[x] = i;
      x = (x << 1) ^ (x & 128 ? 0x11d : 0);
    }
  })();

  function gfMul(a, b) {
    return a === 0 || b === 0 ? 0 : GF256_EXP[GF256_LOG[a] + GF256_LOG[b]];
  }

  function polyMul(p1, p2) {
    const res = new Uint8Array(p1.length + p2.length - 1);
    for (let i = 0; i < p1.length; i++) {
      for (let j = 0; j < p2.length; j++) {
        res[i + j] ^= gfMul(p1[i], p2[j]);
      }
    }
    return res;
  }

  function rsGenPoly(n) {
    let g = new Uint8Array([1]);
    for (let i = 0; i < n; i++) {
      g = polyMul(g, new Uint8Array([1, GF256_EXP[i]]));
    }
    return g;
  }

  function rsEncode(data, ecLen) {
    const gen = rsGenPoly(ecLen);
    const msg = new Uint8Array(data.length + ecLen);
    msg.set(data);
    for (let i = 0; i < data.length; i++) {
      const coef = msg[i];
      if (coef !== 0) {
        for (let j = 0; j < gen.length; j++) {
          msg[i + j] ^= gfMul(gen[j], coef);
        }
      }
    }
    return msg.subarray(data.length);
  }

  // Version specs: [totalCodewords, ecCodewords, [blocks1, data1], [blocks2, data2]]
  // Versions 1 to 10 covering standard UPI URL lengths up to ~300 chars
  const TABLE = [
    null,
    [26, 10, [[1, 16]]],                                   // V1
    [44, 16, [[1, 28]]],                                   // V2
    [70, 26, [[1, 44]]],                                   // V3
    [100, 36, [[2, 32]]],                                  // V4
    [134, 48, [[2, 43]]],                                  // V5
    [172, 64, [[4, 27]]],                                  // V6
    [196, 72, [[4, 31]]],                                  // V7
    [242, 88, [[2, 38], [2, 39]]],                         // V8
    [292, 110, [[3, 36], [2, 37]]],                        // V9
    [346, 130, [[4, 43], [1, 44]]],                        // V10
  ];

  const ALIGNMENT_PATTERNS = [
    [], [], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34], [6, 22, 38], [6, 24, 42], [6, 26, 46], [6, 28, 50]
  ];

  function selectVersion(byteCount) {
    for (let v = 1; v <= 10; v++) {
      const spec = TABLE[v];
      let capacity = 0;
      for (const [blocks, dataPerBlock] of spec[2]) {
        capacity += blocks * dataPerBlock;
      }
      // Byte mode overhead: 4 bits mode + 8 bits length (for V1-9) + 4 bits terminator
      const overhead = v < 10 ? 2 : 3;
      if (capacity >= byteCount + overhead) return v;
    }
    return 10;
  }

  function encodeData(text, version) {
    const encoder = new TextEncoder();
    const bytes = encoder.encode(text);
    const spec = TABLE[version];
    let totalData = 0;
    for (const [blocks, dataPerBlock] of spec[2]) {
      totalData += blocks * dataPerBlock;
    }

    const bits = [];
    function pushBits(val, len) {
      for (let i = len - 1; i >= 0; i--) {
        bits.push((val >> i) & 1);
      }
    }

    // 0100 for Byte Mode
    pushBits(0b0100, 4);
    pushBits(bytes.length, version < 10 ? 8 : 16);
    for (const b of bytes) pushBits(b, 8);

    // Terminator (up to 4 zeroes)
    const totalBits = totalData * 8;
    const termLen = Math.min(4, totalBits - bits.length);
    pushBits(0, termLen);

    // Align to byte
    while (bits.length % 8 !== 0) bits.push(0);

    // Pad bytes 0xEC, 0x11
    const padBytes = [0xEC, 0x11];
    let padIdx = 0;
    while (bits.length < totalBits) {
      pushBits(padBytes[padIdx % 2], 8);
      padIdx++;
    }

    // Convert bits to bytes
    const codewords = new Uint8Array(totalData);
    for (let i = 0; i < totalData; i++) {
      let byte = 0;
      for (let b = 0; b < 8; b++) {
        byte = (byte << 1) | bits[i * 8 + b];
      }
      codewords[i] = byte;
    }

    // Block splitting and Reed-Solomon computation
    const ecPerBlock = spec[1] / spec[2].reduce((acc, x) => acc + x[0], 0);
    const dataBlocks = [];
    const ecBlocks = [];
    let offset = 0;

    for (const [numBlocks, dataLen] of spec[2]) {
      for (let b = 0; b < numBlocks; b++) {
        const block = codewords.subarray(offset, offset + dataLen);
        offset += dataLen;
        dataBlocks.push(block);
        ecBlocks.push(rsEncode(block, ecPerBlock));
      }
    }

    // Interleave codewords
    const finalCodewords = [];
    const maxDataLen = Math.max(...dataBlocks.map(b => b.length));
    for (let i = 0; i < maxDataLen; i++) {
      for (const b of dataBlocks) {
        if (i < b.length) finalCodewords.push(b[i]);
      }
    }
    for (let i = 0; i < ecPerBlock; i++) {
      for (const b of ecBlocks) {
        finalCodewords.push(b[i]);
      }
    }

    return finalCodewords;
  }

  function createMatrix(version) {
    const size = version * 4 + 17;
    const matrix = Array.from({ length: size }, () => Array(size).fill(null));
    const reserved = Array.from({ length: size }, () => Array(size).fill(false));

    function setModule(r, c, val) {
      if (r >= 0 && r < size && c >= 0 && c < size) {
        matrix[r][c] = val ? 1 : 0;
        reserved[r][c] = true;
      }
    }

    // 1. Finder patterns (7x7) + Separators
    function addFinder(top, left) {
      for (let r = -1; r <= 7; r++) {
        for (let c = -1; c <= 7; c++) {
          const row = top + r;
          const col = left + c;
          if (row < 0 || row >= size || col < 0 || col >= size) continue;
          if (r >= 0 && r <= 6 && c >= 0 && c <= 6) {
            const isBorder = (r === 0 || r === 6 || c === 0 || c === 6);
            const isCenter = (r >= 2 && r <= 4 && c >= 2 && c <= 4);
            setModule(row, col, isBorder || isCenter);
          } else {
            setModule(row, col, false);
          }
        }
      }
    }

    addFinder(0, 0);
    addFinder(0, size - 7);
    addFinder(size - 7, 0);

    // 2. Alignment patterns
    const aligns = ALIGNMENT_PATTERNS[version] || [];
    for (let i = 0; i < aligns.length; i++) {
      for (let j = 0; j < aligns.length; j++) {
        const r = aligns[i];
        const c = aligns[j];
        if (reserved[r][c]) continue;
        for (let dr = -2; dr <= 2; dr++) {
          for (let dc = -2; dc <= 2; dc++) {
            const isOuter = Math.abs(dr) === 2 || Math.abs(dc) === 2;
            const isCore = dr === 0 && dc === 0;
            setModule(r + dr, c + dc, isOuter || isCore);
          }
        }
      }
    }

    // 3. Timing patterns
    for (let i = 8; i < size - 8; i++) {
      if (!reserved[6][i]) setModule(6, i, i % 2 === 0);
      if (!reserved[i][6]) setModule(i, 6, i % 2 === 0);
    }

    // Dark module
    setModule(size - 8, 8, true);

    // Reserve format information areas
    for (let i = 0; i < 9; i++) {
      if (i !== 6) {
        reserved[8][i] = true;
        reserved[i][8] = true;
      }
    }
    for (let i = 0; i < 8; i++) {
      reserved[8][size - 1 - i] = true;
      reserved[size - 1 - i][8] = true;
    }

    return { size, matrix, reserved, setModule };
  }

  function placeData(grid, codewords) {
    const { size, matrix, reserved } = grid;
    const bits = [];
    for (const byte of codewords) {
      for (let i = 7; i >= 0; i--) {
        bits.push((byte >> i) & 1);
      }
    }

    let bitIdx = 0;
    let upward = true;

    for (let right = size - 1; right > 0; right -= 2) {
      if (right === 6) right--; // Skip vertical timing column
      const cols = [right, right - 1];
      const rows = [];
      for (let r = 0; r < size; r++) rows.push(upward ? size - 1 - r : r);

      for (const r of rows) {
        for (const c of cols) {
          if (!reserved[r][c]) {
            let bit = bitIdx < bits.length ? bits[bitIdx++] : 0;
            // Apply standard mask 0: (row + col) % 2 === 0
            if ((r + c) % 2 === 0) bit ^= 1;
            matrix[r][c] = bit;
          }
        }
      }
      upward = !upward;
    }

    // Standard format bits for Mask 0, ECC Level M: 101010000010010
    const FORMAT_M_MASK0 = [1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0];
    for (let i = 0; i < 6; i++) matrix[8][i] = FORMAT_M_MASK0[i];
    matrix[8][7] = FORMAT_M_MASK0[6];
    matrix[8][8] = FORMAT_M_MASK0[7];
    matrix[7][8] = FORMAT_M_MASK0[8];
    for (let i = 9; i < 15; i++) matrix[14 - i][8] = FORMAT_M_MASK0[i];

    for (let i = 0; i < 8; i++) matrix[size - 1 - i][8] = FORMAT_M_MASK0[i];
    for (let i = 8; i < 15; i++) matrix[8][size - 15 + i] = FORMAT_M_MASK0[i];
  }

  /**
   * Main render function: creates crisp vector SVG
   */
  window.renderScentedQR = function(containerEl, text, options) {
    if (!containerEl || !text) return;
    options = options || {};
    const sizePx = options.size || 220;
    const margin = options.margin !== undefined ? options.margin : 2;

    const version = selectVersion(new TextEncoder().encode(text).length);
    const codewords = encodeData(text, version);
    const grid = createMatrix(version);
    placeData(grid, codewords);

    const moduleCount = grid.size;
    const totalSize = moduleCount + margin * 2;
    const cellSize = (sizePx / totalSize).toFixed(3);

    // Build SVG path for blazing-fast 60fps single-path rendering
    let pathD = '';
    for (let r = 0; r < moduleCount; r++) {
      for (let c = 0; c < moduleCount; c++) {
        if (grid.matrix[r][c] === 1) {
          const x = (c + margin) * cellSize;
          const y = (r + margin) * cellSize;
          pathD += `M${x},${y}h${cellSize}v${cellSize}h-${cellSize}z `;
        }
      }
    }

    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${sizePx} ${sizePx}" width="${sizePx}" height="${sizePx}" style="display:block; border-radius:6px; background:#ffffff; box-shadow:0 2px 10px rgba(0,0,0,0.06);">
        <rect width="${sizePx}" height="${sizePx}" fill="#FFFFFF"/>
        <path d="${pathD}" fill="#141312"/>
      </svg>
    `;

    containerEl.innerHTML = svg;
  };
})(window);
