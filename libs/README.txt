PDF.js 混合加载说明

本版本的 PDF 导入顺序：
1. 优先加载本地文件：libs/pdf.min.mjs 和 libs/pdf.worker.min.mjs
2. 如果本地文件不存在，联网加载 CDN：jsDelivr / unpkg 上的 pdfjs-dist@5.7.284
3. 如果 CDN 也不可用，降级使用内置轻量 PDF 文本提取器

如果需要真正离线的 PDF.js 最小本地版，请把以下两个文件放到本 libs 目录：
- pdf.min.mjs
- pdf.worker.min.mjs

推荐下载地址：
https://cdn.jsdelivr.net/npm/pdfjs-dist@5.7.284/build/pdf.min.mjs
https://cdn.jsdelivr.net/npm/pdfjs-dist@5.7.284/build/pdf.worker.min.mjs

注意：当前版本只支持文字型 PDF，不支持扫描版/图片版 PDF OCR。
