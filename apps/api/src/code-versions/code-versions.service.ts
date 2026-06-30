import { Injectable, Inject, NotFoundException } from '@nestjs/common';
import { eq, desc } from 'drizzle-orm';
import { randomBytes } from 'node:crypto';
import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { CodeVersionStatus, SourceType } from '@violeteyes/shared';
import { DB_TOKEN, type DB } from '../db/db.module';
import { codeVersions } from '../db/schema';
import { safeExtractZip } from './safe-extract';
import { GitSourceRefSchema, parseSourceRef, injectHttpsToken, type GitSourceRef } from './git-url';

const MAX_UPLOAD_BYTES = 500 * 1024 * 1024;

@Injectable()
export class CodeVersionsService {
  constructor(@Inject(DB_TOKEN) private readonly db: DB) {}

  async list(args: { projectId: string }) {
    return this.db
      .select()
      .from(codeVersions)
      .where(eq(codeVersions.projectId, args.projectId))
      .orderBy(desc(codeVersions.createdAt))
      .all();
  }

  async findById(args: { id: string; projectId?: string }) {
    const row = await this.db
      .select()
      .from(codeVersions)
      .where(eq(codeVersions.id, args.id))
      .limit(1)
      .then((r) => r[0]);
    if (!row) throw new NotFoundException(`code version ${args.id} not found`);
    if (args.projectId && row.projectId !== args.projectId) {
      throw new NotFoundException('code version not in project');
    }
    return row;
  }

  /**
   * 上传 zip 文件并解压。
   *
   * 流程：
   *  1. 保存上传的 zip 到 storage/code-versions/<id>/upload.zip
   *  2. 解压（safeExtractZip，含 zip-bomb / path traversal 防护）
   *  3. 写 code_versions 表（status = ready + sha256）
   *  4. 后台异步跑 LOC 统计（Phase 1.5 实施时补）
   */
  async createFromZip(args: {
    projectId: string;
    uploadedBy: string;
    file: { buffer: Buffer; originalname: string };
  }): Promise<typeof codeVersions.$inferSelect> {
    if (args.file.buffer.length > MAX_UPLOAD_BYTES) {
      throw new Error(`upload exceeds ${MAX_UPLOAD_BYTES} bytes`);
    }

    const id = `cv-${randomBytes(8).toString('hex')}`;
    const storageRoot =
      process.env.CODE_VERSION_DIR ?? join(process.env.STORAGE_DIR ?? './storage', 'code-versions');
    const versionDir = join(storageRoot, id);
    await mkdir(versionDir, { recursive: true });

    const zipPath = join(versionDir, 'upload.zip');
    const { writeFile } = await import('node:fs/promises');
    await writeFile(zipPath, args.file.buffer);

    // 落 status = pending
    const now = Date.now();
    await this.db.insert(codeVersions).values({
      id,
      projectId: args.projectId,
      sourceType: SourceType.ZIP,
      sourceRef: args.file.originalname,
      commitSha: null,
      storagePath: versionDir,
      sizeBytes: args.file.buffer.length,
      fileCount: 0,
      locByLang: {},
      status: CodeVersionStatus.PENDING,
      failureReason: null,
      sha256: '',
      createdBy: args.uploadedBy,
      createdAt: now,
    });

    // 解压（同步，失败回写 status = failed）
    try {
      const result = await safeExtractZip(zipPath, join(versionDir, 'src'));
      await this.db
        .update(codeVersions)
        .set({
          status: CodeVersionStatus.READY,
          sha256: result.sha256,
          fileCount: result.fileCount,
          sizeBytes: result.totalBytes,
          locByLang: {}, // TODO Phase 1.5：跑 LOC 统计
        })
        .where(eq(codeVersions.id, id));
      return this.findById({ id });
    } catch (e) {
      const reason = (e as Error).message;
      await this.db
        .update(codeVersions)
        .set({ status: CodeVersionStatus.FAILED, failureReason: reason })
        .where(eq(codeVersions.id, id));
      throw e;
    }
  }

  /**
   * 从 Git URL 克隆。
   *
   * Phase 1.3 占位：URL 已校验（git-url.ts），真实 git clone 留 Phase 1.3.1。
   * 此版本只创建记录 + 落 status=pending，等待后台 worker。
   */
  async createFromGit(args: {
    projectId: string;
    sourceRef: GitSourceRef;
    credentials?: { username: string; token: string };
    clonedBy: string;
  }): Promise<typeof codeVersions.$inferSelect> {
    const parsed = GitSourceRefSchema.parse(args.sourceRef);
    const urlInfo = parseSourceRef(parsed.url);
    if (!urlInfo) throw new Error('invalid git url');

    const id = `cv-${randomBytes(8).toString('hex')}`;
    const storageRoot =
      process.env.CODE_VERSION_DIR ?? join(process.env.STORAGE_DIR ?? './storage', 'code-versions');
    const versionDir = join(storageRoot, id);
    await mkdir(versionDir, { recursive: true });

    const finalUrl =
      args.credentials && parsed.url.startsWith('https://')
        ? injectHttpsToken(parsed.url, args.credentials.username, args.credentials.token)
        : parsed.url;

    const now = Date.now();
    await this.db.insert(codeVersions).values({
      id,
      projectId: args.projectId,
      sourceType: SourceType.GIT,
      sourceRef: finalUrl,
      commitSha: null,
      storagePath: versionDir,
      sizeBytes: 0,
      fileCount: 0,
      locByLang: {},
      status: CodeVersionStatus.PENDING,
      failureReason: null,
      sha256: '',
      createdBy: args.clonedBy,
      createdAt: now,
    });

    // TODO Phase 1.3.1：spawn `git clone` + `git checkout` + SHA-256 校验
    // 这里只是 placeholder，real worker 在 git-clone.service.ts
    return this.findById({ id });
  }

  /** GitHub URL 是 git:// 的一种特化（owner/repo） */
  async createFromGitHub(args: {
    projectId: string;
    owner: string;
    repo: string;
    ref?: string;
    credentials?: { username: string; token: string };
    clonedBy: string;
  }) {
    // owner/repo 正则校验
    const ownerRe = /^[a-zA-Z0-9][a-zA-Z0-9-]*$/;
    if (!ownerRe.test(args.owner) || !ownerRe.test(args.repo)) {
      throw new Error('invalid GitHub owner/repo');
    }
    const url = `https://github.com/${args.owner}/${args.repo}.git`;
    return this.createFromGit({
      projectId: args.projectId,
      sourceRef: { url, ref: args.ref },
      credentials: args.credentials,
      clonedBy: args.clonedBy,
    });
  }
}