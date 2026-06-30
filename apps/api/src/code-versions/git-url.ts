import { z } from 'zod';

/**
 * Git URL 校验（安全规范）：
 *  - scheme ∈ {https, ssh}
 *  - 拒绝 file:// / git:// / http://
 *  - host 必须为已知格式
 *  - 端口限制（仅 22 / 443）
 */
const ALLOWED_HOSTS_RE = /^[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}$/;

export const GitSourceRefSchema = z.object({
  url: z
    .string()
    .trim()
    .min(1)
    .max(512)
    .refine(
      (s) => s.startsWith('https://') || s.startsWith('git@') || s.startsWith('ssh://'),
      { message: 'url must start with https://, ssh://, or git@' },
    )
    .refine(
      (s) => !s.startsWith('file://') && !s.startsWith('git://') && !s.startsWith('http://'),
      { message: 'disallowed scheme (file/git/http)' },
    ),
  ref: z.string().trim().max(128).optional(), // branch / tag
  credentialsLabel: z.string().trim().max(64).optional(),
});

export type GitSourceRef = z.infer<typeof GitSourceRefSchema>;

export function parseSourceRef(url: string): { host: string; path: string } | null {
  try {
    let u: URL;
    if (url.startsWith('git@')) {
      // git@github.com:owner/repo.git
      const m = url.match(/^git@([^:]+):(.+?)(?:\.git)?$/);
      if (!m) return null;
      const [, host, path] = m;
      if (!ALLOWED_HOSTS_RE.test(host)) return null;
      return { host, path };
    }
    u = new URL(url);
    if (u.protocol !== 'https:' && u.protocol !== 'ssh:') return null;
    if (!ALLOWED_HOSTS_RE.test(u.hostname)) return null;
    // 端口限制
    if (u.port && !['22', '443'].includes(u.port)) return null;
    return { host: u.hostname, path: u.pathname };
  } catch {
    return null;
  }
}

/**
 * 编码 https token 到 URL（仅 username/token，host 已验证）。
 */
export function injectHttpsToken(url: string, username: string, token: string): string {
  const u = new URL(url);
  u.username = encodeURIComponent(username);
  u.password = encodeURIComponent(token);
  return u.toString();
}