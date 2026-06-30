/**
 * 启动时校验所有密钥强度（需求 NFR-SEC-06）。
 *
 * 规则：
 *  - 长度 ≥ 32
 *  - 不同字符数（distinct chars） ≥ 16
 *  - 不能等于默认占位符（防忘改 env）
 *
 * 违反任一规则 → 抛错并退出。
 */
const PLACEHOLDERS = [
  'change-me-in-production',
  'change-me-please-32-chars-min!!',
  'dev-secret-change-me',
  'please-replace-with-32-char-random-hex-please-replace',
];

function distinctCharCount(s: string): number {
  return new Set(s).size;
}

function isPlaceholder(s: string): boolean {
  return PLACEHOLDERS.some((p) => s.includes(p));
}

export function validateSecretsOrThrow(): void {
  const required = [
    { name: 'JWT_SECRET', value: process.env.JWT_SECRET },
    { name: 'APP_MASTER_KEY', value: process.env.APP_MASTER_KEY },
    { name: 'SESSION_SECRET', value: process.env.SESSION_SECRET },
  ];

  const errors: string[] = [];

  for (const { name, value } of required) {
    if (!value || value.length === 0) {
      errors.push(`${name} is empty`);
      continue;
    }
    if (value.length < 32) {
      errors.push(`${name} length ${value.length} < 32`);
    }
    if (distinctCharCount(value) < 16) {
      errors.push(`${name} distinct chars ${distinctCharCount(value)} < 16 (low entropy)`);
    }
    if (isPlaceholder(value)) {
      errors.push(`${name} uses default placeholder — replace before production`);
    }
  }

  // 开发环境额外检查（可关）
  if (process.env.NODE_ENV !== 'development') {
    const { BULL_BOARD_BASIC_PASSWORD } = process.env;
    if (!BULL_BOARD_BASIC_PASSWORD || BULL_BOARD_BASIC_PASSWORD === 'admin') {
      errors.push('BULL_BOARD_BASIC_PASSWORD must be set in non-dev environment');
    }
  }

  if (errors.length > 0) {
    const msg = `[SecretStrength] refusing to start:\n  - ${errors.join('\n  - ')}`;
    throw new Error(msg);
  }
}