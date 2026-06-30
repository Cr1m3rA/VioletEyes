import * as path from 'node:path';
import { createWriteStream } from 'node:fs';
import { mkdir, rm, stat } from 'node:fs/promises';
import { pipeline } from 'node:stream/promises';
import yauzl from 'yauzl';
import { BadRequestException } from '@nestjs/common';

/**
 * Zip-bomb 安全解压（ §6.1 高危修复）。
 *
 * 限制：
 *  - 解压前 ≤ 500MB
 *  - 解压比 ≤ 100（解压后 / 解压前）
 *  - 文件数 ≤ 100,000
 *  - 单文件 ≤ 100MB
 *  - 无 ".." 路径
 *  - 无符号链接（yauzl 默认不解 symlink，但显式断言）
 */

const MAX_ZIP_BYTES = 500 * 1024 * 1024; // 500MB
const MAX_UNZIPPED_BYTES = MAX_ZIP_BYTES * 100;
const MAX_FILES = 100_000;
const MAX_SINGLE_FILE = 100 * 1024 * 1024; // 100MB

export interface SafeExtractResult {
  extractedTo: string;
  totalBytes: number;
  fileCount: number;
  sha256: string;
}

export async function safeExtractZip(
  zipPath: string,
  targetDir: string,
): Promise<SafeExtractResult> {
  const zipStat = await stat(zipPath);
  if (zipStat.size > MAX_ZIP_BYTES) {
    throw new BadRequestException(`zip too large: ${zipStat.size} > ${MAX_ZIP_BYTES}`);
  }

  await mkdir(targetDir, { recursive: true });

  return new Promise<SafeExtractResult>((resolve, reject) => {
    yauzl.open(zipPath, { lazyEntries: true }, (err, zipfile) => {
      if (err || !zipfile) return reject(err ?? new Error('zipfile open failed'));

      let totalBytes = 0;
      let fileCount = 0;
      const hash = require('node:crypto').createHash('sha256');

      zipfile.on('error', reject);
      zipfile.on('end', () => {
        if (totalBytes > MAX_UNZIPPED_BYTES) {
          rm(targetDir, { recursive: true, force: true }).catch(() => {});
          return reject(
            new BadRequestException(
              `zip-bomb: total uncompressed ${totalBytes} > ${MAX_UNZIPPED_BYTES}`,
            ),
          );
        }
        if (totalBytes / zipStat.size > 100) {
          rm(targetDir, { recursive: true, force: true }).catch(() => {});
          return reject(new BadRequestException('zip-bomb: compression ratio > 100'));
        }
        resolve({ extractedTo: targetDir, totalBytes, fileCount, sha256: hash.digest('hex') });
      });

      zipfile.readEntry();
      zipfile.on('entry', (entry: yauzl.Entry) => {
        // 路径安全
        const decodedName = entry.fileName;
        if (decodedName.includes('..')) {
          zipfile.close();
          rm(targetDir, { recursive: true, force: true }).catch(() => {});
          return reject(new BadRequestException(`unsafe path in zip: ${decodedName}`));
        }

        const targetPath = path.join(targetDir, decodedName);
        if (!targetPath.startsWith(targetDir)) {
          zipfile.close();
          rm(targetDir, { recursive: true, force: true }).catch(() => {});
          return reject(new BadRequestException(`path traversal: ${decodedName}`));
        }

        // symlink 防护（yauzl 不会解压 symlink，但显式检查 mode）
        if ((entry.externalFileAttributes >>> 16) & 0o170000 === 0o120000) {
          zipfile.close();
          return reject(new BadRequestException(`symlink not allowed: ${decodedName}`));
        }

        if (entry.uncompressedSize > MAX_SINGLE_FILE) {
          zipfile.close();
          rm(targetDir, { recursive: true, force: true }).catch(() => {});
          return reject(
            new BadRequestException(
              `file too large: ${decodedName} = ${entry.uncompressedSize}`,
            ),
          );
        }

        if (/\/$/.test(decodedName)) {
          // directory
          mkdir(targetPath, { recursive: true }).then(() => zipfile.readEntry());
          return;
        }

        fileCount += 1;
        if (fileCount > MAX_FILES) {
          zipfile.close();
          rm(targetDir, { recursive: true, force: true }).catch(() => {});
          return reject(new BadRequestException(`too many files: > ${MAX_FILES}`));
        }

        zipfile.openReadStream(entry, (err, readStream) => {
          if (err || !readStream) return reject(err ?? new Error('openReadStream failed'));
          mkdir(path.dirname(targetPath), { recursive: true })
            .then(() => {
              const writeStream = createWriteStream(targetPath);
              readStream.on('data', (chunk: Buffer) => {
                totalBytes += chunk.length;
                hash.update(chunk);
              });
              pipeline(readStream, writeStream)
                .then(() => zipfile.readEntry())
                .catch((e) => {
                  zipfile.close();
                  rm(targetDir, { recursive: true, force: true }).catch(() => {});
                  reject(e);
                });
            })
            .catch(reject);
        });
      });
    });
  });
}