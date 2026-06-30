import { Module, Global } from '@nestjs/common';
import Database from 'better-sqlite3';
import { drizzle, type BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import * as schema from './schema';

export const DB_TOKEN = 'DB';
export type DB = BetterSQLite3Database<typeof schema>;

/**
 * SQLite + Drizzle 模块。
 *
 * 修复点：
 *  - WAL mode 显式设置
 *  - journal_size_limit 防止 WAL 无限增长（100MB）
 *  - onModuleDestroy 显式 close（Phase 1.1 实施时补）
 */
@Global()
@Module({
  providers: [
    {
      provide: DB_TOKEN,
      useFactory: (): DB => {
        const url = process.env.DATABASE_URL ?? './storage/violeteyes.db';
        mkdirSync(dirname(url), { recursive: true });

        const sqlite = new Database(url);
        sqlite.pragma('journal_mode = WAL');
        sqlite.pragma('synchronous = NORMAL');
        sqlite.pragma('journal_size_limit = 104857600'); // 100MB
        sqlite.pragma('foreign_keys = ON');

        return drizzle(sqlite, { schema });
      },
    },
  ],
  exports: [DB_TOKEN],
})
export class DbModule {}