import { describe, it, expect } from 'vitest';
import { Severity, SEVERITY_HEX, SEVERITY_ORDER, ScanMode } from './enums';

describe('enums', () => {
  it('severity hex values match VioletEyes report CSS', () => {
    expect(SEVERITY_HEX[Severity.CRITICAL]).toBe('#dc2626');
    expect(SEVERITY_HEX[Severity.HIGH]).toBe('#ea580c');
    expect(SEVERITY_HEX[Severity.MEDIUM]).toBe('#ca8a04');
    expect(SEVERITY_HEX[Severity.LOW]).toBe('#0891b2');
    expect(SEVERITY_HEX[Severity.INFO]).toBe('#64748b');
  });

  it('severity order is lowest → highest', () => {
    expect(SEVERITY_ORDER).toEqual(['info', 'low', 'medium', 'high', 'critical']);
  });

  it('scan mode includes all four values', () => {
    expect(Object.values(ScanMode).sort()).toEqual(['custom', 'deep', 'quick', 'smart']);
  });
});